/* Managed lifetime, TLS, deferred cancellation and cleanup ownership.
   SPDX-License-Identifier: 0BSD */
#include "pthread-internal.h"
#include <unistd.h>
#define KEY_BITS 7
#define KEY_MASK (PTHREAD_KEYS_MAX - 1)
struct key_slot { unsigned long generation; int active; void (*destructor)(void *); };
static struct key_slot keys[PTHREAD_KEYS_MAX];
static struct pt_record initial;
static struct pt_record *records;
struct pt_record *pt_find_locked(pthread_t thread)
{
  struct pt_record *r;
  for (r = records; r && r->thread != thread; r = r->next) {}
  if (!r && thread == cthread_self() && thread && !thread->func && !initial.thread) {
    initial.thread = thread; initial.initial = 1;
    initial.kernel = thread_self(); initial.started = 1;
    initial.next = records; records = &initial; r = &initial;
  }
  return r;
}
struct pt_record *pt_current_locked(void)
{ return pt_find_locked(cthread_self()); }
int pt_cancelled_locked(struct pt_record *r)
{ return r && r->cancel_pending && !r->cancel_disabled && !r->exiting; }
static void unlink_record(struct pt_record *r)
{
  struct pt_record **p;
  for (p = &records; *p && *p != r; p = &(*p)->next) {}
  if (*p) *p = r->next;
}
static int valid_key(pthread_key_t key)
{
  unsigned index = key & KEY_MASK;
  return keys[index].active && keys[index].generation == (key >> KEY_BITS);
}
int ns33_pthread_key_create(pthread_key_t *key, void (*destructor)(void *))
{
  unsigned i;
  if (!key) return EINVAL;
  pt_lock();
  for (i = 0; i < PTHREAD_KEYS_MAX; ++i) {
    /* Never wrap a generation and accidentally revive a deleted key. */
    if (!keys[i].active && keys[i].generation < (ULONG_MAX >> KEY_BITS)) {
      ++keys[i].generation;
      keys[i].active = 1;
      keys[i].destructor = destructor;
      *key = (keys[i].generation << KEY_BITS) | i;
      pt_unlock();
      return 0;
    }
  }
  pt_unlock();
  return EAGAIN;
}
int ns33_pthread_key_delete(pthread_key_t key)
{
  struct pt_record *r;
  unsigned index = key & KEY_MASK;
  pt_lock();
  if (!valid_key(key)) { pt_unlock(); return EINVAL; }
  keys[index].active = 0;
  keys[index].destructor = 0;
  for (r = records; r; r = r->next) r->values[index] = 0;
  pt_unlock();
  return 0;
}
void *ns33_pthread_getspecific(pthread_key_t key)
{
  void *value = 0;
  struct pt_record *r;
  pt_lock();
  if (valid_key(key) && (r = pt_current_locked()) != 0)
    value = r->values[key & KEY_MASK];
  pt_unlock();
  return value;
}
int ns33_pthread_setspecific(pthread_key_t key, const void *value)
{
  struct pt_record *r;
  pt_lock();
  if (!valid_key(key)) { pt_unlock(); return EINVAL; }
  r = pt_current_locked();
  if (!r || r->finished) { pt_unlock(); return ENOTSUP; }
  r->values[key & KEY_MASK] = (void *)value;
  pt_unlock();
  return 0;
}
static void finish_thread(struct pt_record *r, void *result)
{
  unsigned round, i;
  struct ns33_pthread_cleanup *cleanup;
  int dispose;
  pt_lock();
  r->exiting = 1;
  r->cancel_disabled = 1;
  while ((cleanup = r->cleanup) != 0) {
    r->cleanup = cleanup->previous;
    pt_unlock(); cleanup->routine(cleanup->argument); pt_lock();
  }
  pt_unlock();
  for (round = 0; round < PTHREAD_DESTRUCTOR_ITERATIONS; ++round) {
    int invoked = 0;
    for (i = 0; i < PTHREAD_KEYS_MAX; ++i) {
      void *value;
      void (*destructor)(void *);
      pt_lock();
      value = r->values[i]; r->values[i] = 0;
      destructor = keys[i].active ? keys[i].destructor : 0;
      pt_unlock();
      if (value && destructor) { invoked = 1; destructor(value); }
    }
    if (!invoked) break;
  }
  pt_lock();
  memset(r->values, 0, sizeof(r->values));
  pt_sync_thread_exit_locked(r->thread);
  pt_extra_thread_exit_locked(r->thread);
  r->finished = 1; r->result = result;
  (void)pt_wake(&r->joiners, 1);
  dispose = r->detached && !r->initial && !r->creating;
  if (dispose) unlink_record(r);
  pt_unlock();
  if (dispose) free(r);
}
static any_t start_thread(any_t opaque)
{
  struct pt_record *r = opaque;
  void *result = 0;
  pt_lock();
  r->kernel = thread_self(); /* Borrowed cached Mach 2 port name. */
  r->start_error = pt_schedule_other_locked(r->kernel);
  r->started = 1;
  (void)pt_wake(&r->joiners, 1);
  pt_unlock();
  if (!r->start_error) result = r->function(r->argument);
  finish_thread(r, result);
  return result;
}
int ns33_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                        void *(*function)(void *), void *argument)
{
  struct pt_record *r;
  struct pt_waiter started;
  int error, detached, dispose;
  if (!thread || !function) return EINVAL;
  (void)pthread_self();
  r = calloc(1, sizeof(*r));
  if (!r) return EAGAIN;
  r->function = function; r->argument = argument;
  pt_lock();
  (void)pt_current_locked();
  error = cthread_limit() ? ENOTSUP : pt_attr_detached_locked(attr, &detached);
  if (!error) error = pt_schedule_check_locked(thread_self());
  if (!error) error = pt_waiter_init(&started);
  if (error) { pt_unlock(); free(r); return error; }
  r->detached = detached; r->creating = 1;
  r->thread = cthread_fork(start_thread, r);
  if (!r->thread) {
    pt_waiter_destroy(&started); pt_unlock(); free(r); return EAGAIN;
  }
  r->next = records; records = r;
  if (detached) cthread_detach(r->thread);
  /* Publish only after the native worker has an actual kernel identity and
     a qualified scheduling policy. Pin a fast detached record meanwhile. */
  while (!r->started || (r->start_error && !r->finished)) {
    started.notified = 0;
    pt_enqueue(&r->joiners, &started);
    error = pt_wait_locked(&started, 0, 0);
    pt_remove(&r->joiners, &started);
    if (error) { pt_unlock(); abort(); }
  }
  pt_waiter_destroy(&started);
  error = r->start_error;
  r->creating = 0;
  (void)pt_wake(&r->joiners, 1);
  if (error) {
    if (!detached) (void)cthread_join(r->thread);
    unlink_record(r); dispose = 1;
  } else {
    *thread = r->thread;
    dispose = r->detached && r->finished;
    if (dispose) unlink_record(r);
  }
  pt_unlock();
  if (dispose) free(r);
  return error;
}
int ns33_pthread_join(pthread_t thread, void **result)
{
  struct pt_record *r, *self;
  struct pt_waiter waiter;
  void *value;
  int error = 0, native_join;
  pthread_testcancel();
  if (thread == pthread_self()) return EDEADLK;
  pt_lock(); r = pt_find_locked(thread); self = pt_current_locked();
  if (!r) { pt_unlock(); return ESRCH; }
  if (r->detached || r->joining) { pt_unlock(); return EINVAL; }
  r->joining = 1;
  if (!r->finished || r->creating) {
    error = pt_waiter_init(&waiter);
    if (!error) {
      while ((!r->finished || r->creating) && !pt_cancelled_locked(self)) {
        waiter.notified = 0;
        pt_enqueue(&r->joiners, &waiter);
        error = pt_wait_locked(&waiter, 0, 1);
        pt_remove(&r->joiners, &waiter);
        if (error) break;
      }
      pt_remove(&r->joiners, &waiter);
      pt_waiter_destroy(&waiter);
    }
  }
  if (error || pt_cancelled_locked(self)) {
    r->joining = 0; pt_unlock(); pthread_testcancel(); return error;
  }
  value = r->result; native_join = !r->initial;
  /* Retain the claim until native reclamation is complete. */
  if (native_join) (void)cthread_join(thread);
  unlink_record(r); pt_unlock();
  if (native_join) free(r);
  if (result) *result = value;
  return 0;
}
int ns33_pthread_detach(pthread_t thread)
{
  struct pt_record *r;
  int dispose;
  pt_lock(); r = pt_find_locked(thread);
  if (!r) { pt_unlock(); return ESRCH; }
  if (r->detached || r->joining) { pt_unlock(); return EINVAL; }
  r->detached = 1;
  if (!r->initial) cthread_detach(thread);
  dispose = r->finished && !r->initial && !r->creating;
  if (dispose) unlink_record(r);
  pt_unlock();
  if (dispose) free(r);
  return 0;
}
void ns33_pthread_exit(void *result)
{
  struct pt_record *r;
  int is_initial;
  pt_lock(); r = pt_current_locked();
  is_initial = r && r->initial;
  pt_unlock();
  if (r) finish_thread(r, result);
  /* Native main-thread exit waits for workers, then uses this value as the
     process exit status. POSIX requires zero for the last pthread_exit. */
  cthread_exit(is_initial ? 0 : result);
  abort();
}
int ns33_pthread_cancel(pthread_t thread)
{
  struct pt_record *r;
  int error = 0;
  pt_lock(); r = pt_find_locked(thread);
  if (!r) error = ESRCH;
  else if (!r->finished && !r->exiting) {
    r->cancel_pending = 1;
    if (!r->cancel_disabled && r->waiting) error = pt_notify(r->waiting, 0);
  }
  pt_unlock(); return error;
}
void ns33_pthread_testcancel(void)
{
  int cancelled;
  pt_lock(); cancelled = pt_cancelled_locked(pt_current_locked()); pt_unlock();
  if (cancelled) pthread_exit(PTHREAD_CANCELED);
}
int ns33_pthread_setcancelstate(int state, int *old)
{
  struct pt_record *r;
  if (state != PTHREAD_CANCEL_ENABLE && state != PTHREAD_CANCEL_DISABLE) return EINVAL;
  pt_lock(); r = pt_current_locked();
  if (!r) { pt_unlock(); return ENOTSUP; }
  if (old) *old = r->cancel_disabled ? PTHREAD_CANCEL_DISABLE : PTHREAD_CANCEL_ENABLE;
  r->cancel_disabled = state == PTHREAD_CANCEL_DISABLE;
  pt_unlock();
  /* Changing state is not a deferred cancellation point. */
  return 0;
}
int ns33_pthread_setcanceltype(int type, int *old)
{
  if (type != PTHREAD_CANCEL_DEFERRED && type != PTHREAD_CANCEL_ASYNCHRONOUS) return EINVAL;
  if (type == PTHREAD_CANCEL_ASYNCHRONOUS) return ENOTSUP;
  if (old) *old = PTHREAD_CANCEL_DEFERRED;
  return 0;
}
void ns33_pthread_cleanup_push(struct ns33_pthread_cleanup *c,
                              void (*fn)(void *), void *arg)
{
  struct pt_record *r;
  c->routine = fn; c->argument = arg; c->previous = 0;
  pt_lock(); r = pt_current_locked();
  if (r) { c->previous = r->cleanup; r->cleanup = c; }
  pt_unlock();
}
void ns33_pthread_cleanup_pop(struct ns33_pthread_cleanup *c, int execute)
{
  struct pt_record *r;
  pt_lock(); r = pt_current_locked();
  if (r) {
    if (r->cleanup != c) { pt_unlock(); abort(); }
    r->cleanup = c->previous;
  }
  pt_unlock();
  if (execute) c->routine(c->argument);
}

struct atfork_handler {
  struct atfork_handler *older, *newer;
  void (*prepare)(void), (*parent)(void), (*child)(void);
};
static struct atfork_handler *fork_first, *fork_last;
int ns33_pthread_atfork(void (*prepare)(void), void (*parent)(void), void (*child)(void))
{
  struct atfork_handler *h = malloc(sizeof(*h));
  if (!h) return ENOMEM;
  h->prepare = prepare; h->parent = parent; h->child = child;
  pt_lock();
  h->older = fork_last; h->newer = 0;
  if (fork_last) fork_last->newer = h; else fork_first = h;
  fork_last = h;
  pt_unlock();
  return 0;
}
/* Native fork already brackets its syscall with Cthread/malloc fork hooks.
   This separate binding avoids calling our public wrapper recursively. */
extern pid_t pt_native_fork(void) __asm__("_fork");
pid_t ns33_fork(void)
{
  struct atfork_handler *h, *first, *last;
  struct pt_record *self, *r, *next;
  int saved_errno;
  pid_t pid;
  pt_lock(); first = fork_first; last = fork_last; pt_unlock();
  /* Entries never move or disappear. Older links are immutable; newer links
     are immutable before the captured last entry. Stop at that boundary so
     registrations made by callbacks belong to the next fork. No allocation
     or user callback executes while pt_gate is held. */
  for (h = last; h; h = h->older) if (h->prepare) h->prepare();
  pt_lock(); self = pt_current_locked();
  pid = pt_native_fork();
  saved_errno = pid < 0 ? cthread_errno() : errno;
  if (!pid) {
    /* Other threads do not survive fork. Retain calling-thread TLS and
       cleanup frames; never run vanished threads' destructors in the child. */
    for (r = records; r; r = next) {
      next = r->next;
      if (r != self && r != &initial) free(r);
    }
    if (self) {
      self->next = 0; self->initial = 1; self->joining = 0;
      self->waiting = 0; self->creating = 0;
      self->kernel = thread_self();
      memset(&self->joiners, 0, sizeof(self->joiners));
    }
    records = self;
    pt_sync_fork_child();
    pt_extra_fork_child();
  }
  pt_unlock();
  for (h = first; h;) {
    void (*fn)(void) = pid == 0 ? h->child : h->parent;
    if (fn) fn();
    if (h == last) break;
    h = h->newer;
  }
  if (pid < 0) cthread_set_errno_self(saved_errno);
  errno = saved_errno;
  return pid;
}
