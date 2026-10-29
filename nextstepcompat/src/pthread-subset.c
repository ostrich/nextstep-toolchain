/* Process-private synchronization over Mach ports. Public object layouts from
   ABI minor 5 are retained; private state is allocated lazily and destroyed
   only after the object is idle. Native and pthread operations must not be
   mixed on the same mutex or condition. SPDX-License-Identifier: 0BSD */
#include "pthread-internal.h"

static struct mutex pt_gate = MUTEX_INITIALIZER;
static struct mutex initialization_lock = MUTEX_INITIALIZER;
static int initialized;

void pt_fence(void)
{
#if defined(__hppa__)
  __asm__ volatile("sync" ::: "memory");
#elif defined(__sparc__)
  __asm__ volatile("stbar" ::: "memory");
#else
  __asm__ volatile("" ::: "memory");
#endif
}
static void initialize(void)
{
  /* The shipped SPARC spin_lock loops on its address register after a
     collision. The native nonblocking atomic primitive is correct. */
  while (!mutex_try_lock(&initialization_lock)) {}
  pt_fence();
  if (!initialized) { cthread_init(); initialized = 1; }
  pt_fence();
  *(volatile int *)&initialization_lock.lock = 0;
}
void pt_lock(void)
{
  initialize();
  if (!mutex_try_lock(&pt_gate)) mutex_wait_lock(&pt_gate);
  pt_fence();
}
void pt_unlock(void)
{
  pt_fence();
  *(volatile int *)&pt_gate.lock = 0;
}
pthread_t ns33_pthread_self(void) { initialize(); return cthread_self(); }
int ns33_pthread_equal(pthread_t a, pthread_t b) { return a == b; }

int pt_waiter_init(struct pt_waiter *w)
{
  memset(w, 0, sizeof(*w));
  return port_allocate(task_self(), &w->port) == KERN_SUCCESS ? 0 : EAGAIN;
}
void pt_waiter_destroy(struct pt_waiter *w)
{ (void)port_deallocate(task_self(), w->port); }
void pt_enqueue(struct pt_queue *q, struct pt_waiter *w)
{
  w->next = 0;
  if (q->tail) q->tail->next = w; else q->head = w;
  q->tail = w;
}
void pt_remove(struct pt_queue *q, struct pt_waiter *w)
{
  struct pt_waiter **p = &q->head, *previous = 0;
  while (*p && *p != w) { previous = *p; p = &(*p)->next; }
  if (*p) { *p = w->next; if (q->tail == w) q->tail = previous; }
}
int pt_notify(struct pt_waiter *w, int notified)
{
  msg_header_t message;
  if (!w->sent) {
    memset(&message, 0, sizeof(message));
    message.msg_simple = 1;
    message.msg_size = sizeof(message);
    message.msg_remote_port = w->port;
    if (msg_send(&message, SEND_TIMEOUT, 0) != SEND_SUCCESS) return EIO;
    w->sent = 1;
  }
  if (notified) w->notified = 1;
  return 0;
}
int pt_wake(struct pt_queue *q, int all)
{
  int error;
  while (q->head) {
    struct pt_waiter *w = q->head;
    if ((error = pt_notify(w, 1))) return error;
    pt_remove(q, w);
    if (!all) break;
  }
  return 0;
}
int pt_deadline_valid(const struct timespec *t)
{ return !t || t->tv_nsec < 0 || t->tv_nsec >= 1000000000L ? EINVAL : 0; }
static int deadline_ms(const struct timespec *t, unsigned *ms)
{
  struct timeval now;
  long long remaining;
  if (gettimeofday(&now, 0)) return EIO;
  remaining = ((long long)t->tv_sec - now.tv_sec) * 1000000
              + (t->tv_nsec + 999) / 1000 - now.tv_usec;
  if (remaining <= 0) return ETIMEDOUT;
  /* Recheck wall-clock adjustments at least once a second. */
  *ms = remaining > 1000000 ? 1000 : (unsigned)((remaining + 999) / 1000);
  return 0;
}
int pt_deadline_expired(const struct timespec *t)
{ unsigned ms; return deadline_ms(t, &ms); }
int pt_wait_locked(struct pt_waiter *w, const struct timespec *deadline,
                   int cancellable)
{
  struct pt_record *r = cancellable ? pt_current_locked() : 0;
  int error = 0, status;
  unsigned ms = 0;
  msg_header_t message;
  if (r) r->waiting = w;
  for (;;) {
    if (cancellable && pt_cancelled_locked(r)) break;
    if (w->notified) break;
    if (deadline && (error = deadline_ms(deadline, &ms))) break;
    pt_unlock();
    memset(&message, 0, sizeof(message));
    message.msg_size = sizeof(message);
    message.msg_local_port = w->port;
    status = msg_receive(&message, deadline ? RCV_TIMEOUT : 0, ms);
    pt_lock();
    w->sent = 0;
    if (status != RCV_SUCCESS && status != RCV_TIMED_OUT &&
        status != RCV_INTERRUPTED) { error = EIO; break; }
  }
  if (r) r->waiting = 0;
  return error;
}

struct pt_mutex {
  struct pt_mutex *next;
  pthread_mutex_t *object;
  pthread_t owner;
  unsigned depth, users;
  int type, robust, inconsistent;
  struct pt_queue waiters;
};
struct pt_cond {
  struct pt_cond *next;
  pthread_cond_t *object;
  pthread_mutex_t *binding;
  unsigned users;
  struct pt_queue waiters;
};
static struct pt_mutex *mutexes;
static struct pt_cond *conditions;
static struct pt_mutex *mutex_state(pthread_mutex_t *m)
{
  struct pt_mutex *s;
  if (m->name == PT_DESTROYED) return 0;
  if (m->name) return (struct pt_mutex *)m->name;
  s = calloc(1, sizeof(*s));
  if (s) {
    s->object = m; s->next = mutexes; mutexes = s;
    m->name = (char *)s;
  }
  return s;
}
static struct pt_cond *cond_state(pthread_cond_t *c)
{
  struct pt_cond *s;
  if (c->name == PT_DESTROYED) return 0;
  if (c->name) return (struct pt_cond *)c->name;
  s = calloc(1, sizeof(*s));
  if (s) {
    s->object = c; s->next = conditions; conditions = s;
    c->name = (char *)s;
  }
  return s;
}
int ns33_pthread_mutex_init(pthread_mutex_t *m, const pthread_mutexattr_t *a)
{
  struct pt_mutex *s;
  if (!m || (a && (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR)) return EINVAL;
  memset(m, 0, sizeof(*m));
  if (!a || !(a->reserved & 7)) return 0;
  pt_lock(); s = mutex_state(m);
  if (s) { s->type = a->reserved & 3; s->robust = !!(a->reserved & 4); }
  pt_unlock();
  return s ? 0 : ENOMEM;
}
static int mutex_release(struct pt_mutex *s)
{
  if (s->owner != cthread_self()) return EPERM;
  if (--s->depth) return 0;
  s->owner = 0;
  if (s->robust && s->inconsistent) s->inconsistent = 2;
  return pt_wake(&s->waiters, s->inconsistent == 2);
}
static int mutex_acquire(struct pt_mutex *s, const struct timespec *t, int try,
                         struct pt_waiter *spare)
{
  pthread_t self = cthread_self();
  struct pt_waiter local, *waiter = spare ? spare : &local;
  int error;
  if (s->robust && !pt_current_locked()) return ENOTSUP;
  if (s->inconsistent == 2) return ENOTRECOVERABLE;
  if (s->owner == self && s->type == PTHREAD_MUTEX_RECURSIVE) {
    if (s->depth == UINT_MAX) return EAGAIN;
    ++s->depth; return 0;
  }
  if (!s->owner) { s->owner = self; s->depth = 1; return s->inconsistent ? EOWNERDEAD : 0; }
  if (try) return EBUSY;
  if (s->owner == self && s->type == PTHREAD_MUTEX_ERRORCHECK) return EDEADLK;
  if (t && (error = pt_deadline_valid(t))) return error;
  if (!spare && (error = pt_waiter_init(waiter))) return error;
  error = 0;
  ++s->users;
  while (s->owner) {
    waiter->notified = 0;
    pt_enqueue(&s->waiters, waiter);
    error = pt_wait_locked(waiter, t, 0);
    pt_remove(&s->waiters, waiter);
    if (s->inconsistent == 2) error = ENOTRECOVERABLE;
    if (error) break;
  }
  if (!error && t) error = pt_deadline_expired(t);
  --s->users;
  if (error && !s->owner) (void)pt_wake(&s->waiters, 0);
  if (!spare) pt_waiter_destroy(waiter);
  if (!error) { s->owner = self; s->depth = 1; if (s->inconsistent) error = EOWNERDEAD; }
  return error;
}
static int mutex_op(pthread_mutex_t *m, const struct timespec *t, int try)
{
  struct pt_mutex *s;
  int error;
  if (!m) return EINVAL;
  pt_lock(); s = mutex_state(m);
  error = s ? mutex_acquire(s, t, try, 0) : (m->name == PT_DESTROYED ? EINVAL : ENOMEM);
  pt_unlock(); return error;
}
int ns33_pthread_mutex_lock(pthread_mutex_t *m) { return mutex_op(m, 0, 0); }
int ns33_pthread_mutex_trylock(pthread_mutex_t *m) { return mutex_op(m, 0, 1); }
int ns33_pthread_mutex_timedlock(pthread_mutex_t *m, const struct timespec *t)
{ if (!t) return EINVAL; return mutex_op(m, t, 0); }
int ns33_pthread_mutex_unlock(pthread_mutex_t *m)
{
  int error;
  struct pt_mutex *s;
  if (!m) return EINVAL;
  pt_lock(); s = mutex_state(m);
  error = s ? mutex_release(s) : EINVAL;
  pt_unlock(); return error;
}
int ns33_pthread_mutex_destroy(pthread_mutex_t *m)
{
  struct pt_mutex *s, **link;
  int error = 0;
  if (!m) return EINVAL;
  pt_lock();
  if (m->name == PT_DESTROYED) error = EINVAL;
  else if ((s = (struct pt_mutex *)m->name) != 0) {
    if (s->owner || s->users) error = EBUSY;
    else {
      for (link = &mutexes; *link != s; link = &(*link)->next) {}
      *link = s->next; free(s);
    }
  }
  if (!error) m->name = PT_DESTROYED;
  pt_unlock(); return error;
}
int ns33_pthread_cond_init(pthread_cond_t *c, const pthread_condattr_t *a)
{
  if (!c || (a && a->reserved != PT_COND_ATTR)) return EINVAL;
  memset(c, 0, sizeof(*c)); return 0;
}
int ns33_pthread_cond_destroy(pthread_cond_t *c)
{
  struct pt_cond *s, **link;
  int error = 0;
  if (!c) return EINVAL;
  pt_lock();
  if (c->name == PT_DESTROYED) error = EINVAL;
  else if ((s = (struct pt_cond *)c->name) != 0) {
    if (s->users) error = EBUSY;
    else {
      for (link = &conditions; *link != s; link = &(*link)->next) {}
      *link = s->next; free(s);
    }
  }
  if (!error) c->name = PT_DESTROYED;
  pt_unlock(); return error;
}
static int cond_wait(pthread_cond_t *c, pthread_mutex_t *m, const struct timespec *t)
{
  struct pt_cond *s;
  struct pt_mutex *mutex;
  struct pt_waiter waiter;
  struct pt_record *r;
  int error, cancelled, signaled;
  if (!c || !m || (t && pt_deadline_valid(t))) return EINVAL;
  pt_lock(); s = cond_state(c); mutex = mutex_state(m);
  if (!s || !mutex) { pt_unlock(); return EINVAL; }
  if (mutex->owner != cthread_self()) { pt_unlock(); return EPERM; }
  /* Recursive waits release just one ownership level, matching POSIX. A
     depth above one can therefore prevent a producer from acquiring it. */
  if (s->waiters.head && s->binding != m) { pt_unlock(); return EINVAL; }
  if ((error = pt_waiter_init(&waiter))) { pt_unlock(); return error; }
  r = pt_current_locked();
  s->binding = m; ++s->users;
  ++mutex->users; /* Pins the mutex while it is released. */
  pt_enqueue(&s->waiters, &waiter);
  error = mutex_release(mutex);
  if (!error) error = pt_wait_locked(&waiter, t, 1);
  pt_remove(&s->waiters, &waiter);
  signaled = waiter.notified;
  /* Keep the object pinned until mutex reacquisition completes. */
  {
    int acquire_error = mutex_acquire(mutex, 0, 0, &waiter);
    if (acquire_error == EOWNERDEAD || acquire_error == ENOTRECOVERABLE) error = acquire_error;
    else if (acquire_error) { pt_unlock(); abort(); }
  }
  pt_waiter_destroy(&waiter);
  cancelled = pt_cancelled_locked(r);
  /* Do not consume a concurrent signal if cancellation wins this wait. */
  if (cancelled && signaled) (void)pt_wake(&s->waiters, 0);
  --mutex->users;
  if (!--s->users) s->binding = 0;
  pt_unlock();
  if (cancelled) pthread_testcancel();
  return error;
}
int ns33_pthread_cond_wait(pthread_cond_t *c, pthread_mutex_t *m)
{ return cond_wait(c, m, 0); }
int ns33_pthread_cond_timedwait(pthread_cond_t *c, pthread_mutex_t *m, const struct timespec *t)
{ if (!t) return EINVAL; return cond_wait(c, m, t); }
static int cond_wake(pthread_cond_t *c, int all)
{
  struct pt_cond *s;
  int error;
  if (!c) return EINVAL;
  pt_lock();
  if (c->name == PT_DESTROYED) error = EINVAL;
  else {
    s = (struct pt_cond *)c->name;
    error = s ? pt_wake(&s->waiters, all) : 0;
  }
  pt_unlock(); return error;
}
int ns33_pthread_cond_signal(pthread_cond_t *c) { return cond_wake(c, 0); }
int ns33_pthread_cond_broadcast(pthread_cond_t *c) { return cond_wake(c, 1); }
/* An initializer owns a transient record. It must not live on its stack:
   native fork can unmap vanished Cproc stacks before our child hook runs.
   Completed once objects retain no heap state and need no destroy API. */
struct pt_once_running {
  struct pt_once_running *next;
  pthread_once_t *object;
  pthread_t owner;
};
static struct pt_once_running *running_once;
static struct pt_queue once_waiters;
static void once_wake(pthread_once_t *once)
{
  struct pt_waiter *w = once_waiters.head, *next;
  while (w) {
    next = w->next;
    if (w->channel == once && !pt_notify(w, 1)) pt_remove(&once_waiters, w);
    w = next;
  }
}
static void once_finish(struct pt_once_running *state, int complete)
{
  struct pt_once_running **p;
  pt_lock();
  for (p = &running_once; *p && *p != state; p = &(*p)->next) {}
  if (*p) *p = state->next;
  state->object->done = complete;
  once_wake(state->object);
  free(state);
  pt_unlock();
}
static void once_reset(void *arg) { once_finish(arg, 0); }
int ns33_pthread_once(pthread_once_t *once, void (*function)(void))
{
  struct pt_once_running *state, *p;
  struct ns33_pthread_cleanup cleanup;
  struct pt_waiter waiter;
  int error = 0, waiting = 0;
  if (!once || !function) return EINVAL;
  pt_lock();
  for (;;) {
    if (once->done) break;
    for (p = running_once; p && p->object != once; p = p->next) {}
    if (!p) {
      state = malloc(sizeof(*state));
      if (!state) { error = ENOMEM; break; }
      if (waiting) pt_waiter_destroy(&waiter);
      state->object = once; state->owner = cthread_self();
      state->next = running_once; running_once = state;
      pt_unlock();
      ns33_pthread_cleanup_push(&cleanup, once_reset, state);
      function();
      once_finish(state, 1);
      ns33_pthread_cleanup_pop(&cleanup, 0);
      return 0;
    }
    if (p->owner == cthread_self()) { error = EDEADLK; break; }
    if (!waiting) {
      if ((error = pt_waiter_init(&waiter))) break;
      waiting = 1; waiter.channel = once;
    }
    waiter.notified = 0;
    pt_enqueue(&once_waiters, &waiter);
    error = pt_wait_locked(&waiter, 0, 0);
    pt_remove(&once_waiters, &waiter);
    if (error) break;
  }
  if (waiting) pt_waiter_destroy(&waiter);
  pt_unlock(); return error;
}
/* Called in the child after native libc has repaired Cthreads and malloc.
   Never unlock an application mutex held by a vanished thread. */
void pt_sync_fork_child(void)
{
  struct pt_mutex *m;
  struct pt_cond *c;
  struct pt_once_running **p;
  for (p = &running_once; *p;) {
    if ((*p)->owner != cthread_self()) {
      struct pt_once_running *vanished = *p;
      *p = vanished->next; free(vanished);
    } else p = &(*p)->next;
  }
  memset(&once_waiters, 0, sizeof(once_waiters));
  for (m = mutexes; m; m = m->next) {
    memset(&m->waiters, 0, sizeof(m->waiters)); m->users = 0;
    if (m->owner && m->owner != cthread_self()) m->owner = PT_ENDED_OWNER;
  }
  for (c = conditions; c; c = c->next) {
    memset(&c->waiters, 0, sizeof(c->waiters)); c->users = 0; c->binding = 0;
  }
}

int ns33_pthread_mutex_consistent(pthread_mutex_t *m)
{
  struct pt_mutex *s;
  int error = EINVAL;
  if (!m) return EINVAL;
  pt_lock(); s = (struct pt_mutex *)m->name;
  if (s && s != PT_DESTROYED && s->robust &&
      s->owner == cthread_self() && s->inconsistent == 1) {
    s->inconsistent = 0; error = 0;
  }
  pt_unlock(); return error;
}
void pt_sync_thread_exit_locked(pthread_t thread)
{
  struct pt_mutex *m;
  for (m = mutexes; m; m = m->next) if (m->owner == thread) {
    if (m->robust) {
      m->owner = 0; m->depth = 0; m->inconsistent = 1;
      (void)pt_wake(&m->waiters, 0);
    } else {
      /* A terminated owner's native handle can be recycled. Keep a stalled
         mutex locked without mistaking the new incarnation for its owner. */
      m->owner = PT_ENDED_OWNER;
    }
  }
}
