/* Process-private rwlocks, barriers and native spin locks.
   SPDX-License-Identifier: 0BSD */
#include "pthread-internal.h"
struct reader {
  struct reader *next;
  pthread_t thread;
  unsigned depth;
};
struct rwstate {
  struct rwstate *next;
  struct reader *readers;
  pthread_t writer;
  unsigned users, writers;
  struct pt_queue waiters;
};
struct barrierstate {
  struct barrierstate *next;
  unsigned count, arrived, users;
  struct pt_queue waiters;
};
static struct rwstate *rwlocks;
static struct barrierstate *barriers;
static struct rwstate *rwstate(pthread_rwlock_t *lock)
{
  struct rwstate *s;
  if (lock->state == PT_DESTROYED) return 0;
  if (lock->state) return lock->state;
  s = calloc(1, sizeof(*s));
  if (s) { s->next = rwlocks; rwlocks = s; lock->state = s; }
  return s;
}
int ns33_pthread_rwlock_init(pthread_rwlock_t *lock, const pthread_rwlockattr_t *a)
{
  if (!lock || (a && a->reserved != PT_RW_ATTR)) return EINVAL;
  lock->state = 0; return 0;
}
int ns33_pthread_rwlock_destroy(pthread_rwlock_t *lock)
{
  struct rwstate *s, **p;
  int error = 0;
  if (!lock) return EINVAL;
  pt_lock(); s = lock->state;
  if (s == PT_DESTROYED) error = EINVAL;
  else if (s) {
    if (s->readers || s->writer || s->users) error = EBUSY;
    else {
      for (p = &rwlocks; *p != s; p = &(*p)->next) {}
      *p = s->next; free(s);
    }
  }
  if (!error) lock->state = PT_DESTROYED;
  pt_unlock(); return error;
}
static int rw_acquire(pthread_rwlock_t *lock, int write, int try,
                      const struct timespec *deadline)
{
  struct rwstate *s;
  struct reader *r, *fresh = 0;
  struct pt_waiter waiter;
  pthread_t self = pthread_self();
  int error = 0, waiting = 0;
  if (!lock) return EINVAL;
  pt_lock(); s = rwstate(lock);
  if (!s) { pt_unlock(); return lock->state == PT_DESTROYED ? EINVAL : ENOMEM; }
  for (r = s->readers; r && r->thread != self; r = r->next) {}
  if (s->writer == self || (write && r)) {
    pt_unlock(); return try ? EBUSY : EDEADLK;
  }
  if (!write && r && r->depth == UINT_MAX) { pt_unlock(); return EAGAIN; }
  if (!write && !r) {
    fresh = malloc(sizeof(*fresh));
    if (!fresh) { pt_unlock(); return ENOMEM; }
    fresh->thread = self; fresh->depth = 0;
  }
  while (s->writer || (write ? s->readers != 0 : s->writers && !r)) {
    if (try) { error = EBUSY; break; }
    if (!waiting) {
      if (deadline && (error = pt_deadline_valid(deadline))) break;
      if ((error = pt_waiter_init(&waiter))) break;
      waiting = 1; ++s->users; if (write) ++s->writers;
    }
    waiter.notified = 0; pt_enqueue(&s->waiters, &waiter);
    error = pt_wait_locked(&waiter, deadline, 0);
    pt_remove(&s->waiters, &waiter);
    if (error) break;
  }
  if (waiting && !error && deadline) error = pt_deadline_expired(deadline);
  if (waiting) {
    --s->users;
    if (write && !--s->writers) (void)pt_wake(&s->waiters, 1);
    pt_waiter_destroy(&waiter);
    if (error && !s->writer) (void)pt_wake(&s->waiters, 1);
  }
  if (!error) {
    if (write) s->writer = self;
    else {
      if (!r) { r = fresh; fresh = 0; r->next = s->readers; s->readers = r; }
      ++r->depth;
    }
  }
  free(fresh); pt_unlock(); return error;
}
int ns33_pthread_rwlock_rdlock(pthread_rwlock_t *l) { return rw_acquire(l, 0, 0, 0); }
int ns33_pthread_rwlock_wrlock(pthread_rwlock_t *l) { return rw_acquire(l, 1, 0, 0); }
int ns33_pthread_rwlock_tryrdlock(pthread_rwlock_t *l) { return rw_acquire(l, 0, 1, 0); }
int ns33_pthread_rwlock_trywrlock(pthread_rwlock_t *l) { return rw_acquire(l, 1, 1, 0); }
int ns33_pthread_rwlock_timedrdlock(pthread_rwlock_t *l, const struct timespec *t)
{ return t ? rw_acquire(l, 0, 0, t) : EINVAL; }
int ns33_pthread_rwlock_timedwrlock(pthread_rwlock_t *l, const struct timespec *t)
{ return t ? rw_acquire(l, 1, 0, t) : EINVAL; }
int ns33_pthread_rwlock_unlock(pthread_rwlock_t *l)
{
  struct rwstate *s;
  struct reader **p, *r;
  pthread_t self = pthread_self();
  int error = 0;
  if (!l) return EINVAL;
  pt_lock(); s = l->state;
  if (!s || s == PT_DESTROYED) { pt_unlock(); return EINVAL; }
  if (s->writer == self) s->writer = 0;
  else {
    for (p = &s->readers; *p && (*p)->thread != self; p = &(*p)->next) {}
    r = *p;
    if (!r) { pt_unlock(); return EPERM; }
    if (!--r->depth) { *p = r->next; free(r); }
  }
  if (!s->writer) error = pt_wake(&s->waiters, 1);
  pt_unlock(); return error;
}
int ns33_pthread_barrier_init(pthread_barrier_t *b, const pthread_barrierattr_t *a, unsigned n)
{
  struct barrierstate *s;
  if (!b || !n || (a && a->reserved != PT_BARRIER_ATTR)) return EINVAL;
  s = calloc(1, sizeof(*s));
  if (!s) return ENOMEM;
  s->count = n;
  pt_lock(); s->next = barriers; barriers = s; b->state = s; pt_unlock();
  return 0;
}
int ns33_pthread_barrier_destroy(pthread_barrier_t *b)
{
  struct barrierstate *s, **p;
  if (!b) return EINVAL;
  pt_lock(); s = b->state;
  if (!s || s == PT_DESTROYED) { pt_unlock(); return EINVAL; }
  if (s->users) { pt_unlock(); return EBUSY; }
  for (p = &barriers; *p != s; p = &(*p)->next) {}
  *p = s->next; b->state = PT_DESTROYED; pt_unlock(); free(s); return 0;
}
int ns33_pthread_barrier_wait(pthread_barrier_t *b)
{
  struct barrierstate *s;
  struct pt_waiter waiter;
  int error;
  if (!b) return EINVAL;
  pt_lock(); s = b->state;
  if (!s || s == PT_DESTROYED) { pt_unlock(); return EINVAL; }
  /* Allocate before committing an arrival: resource failure cannot strand
     other threads behind a count which includes a non-participant. */
  if ((error = pt_waiter_init(&waiter))) { pt_unlock(); return error; }
  ++s->users;
  if (++s->arrived == s->count) {
    s->arrived = 0; error = pt_wake(&s->waiters, 1);
    if (!error) error = PTHREAD_BARRIER_SERIAL_THREAD;
  } else {
    pt_enqueue(&s->waiters, &waiter);
    error = pt_wait_locked(&waiter, 0, 0);
    pt_remove(&s->waiters, &waiter);
  }
  --s->users; pt_waiter_destroy(&waiter); pt_unlock(); return error;
}
int ns33_pthread_spin_init(pthread_spinlock_t *s, int shared)
{
  if (!s || (shared != PTHREAD_PROCESS_PRIVATE && shared != PTHREAD_PROCESS_SHARED)) return EINVAL;
  if (shared == PTHREAD_PROCESS_SHARED) return ENOTSUP;
  memset(s, 0, sizeof(*s)); return 0;
}
int ns33_pthread_spin_lock(pthread_spinlock_t *s)
{ if (!s) return EINVAL; while (!mutex_try_lock(s)) {} pt_fence(); return 0; }
int ns33_pthread_spin_trylock(pthread_spinlock_t *s)
{ if (!s) return EINVAL; if (!mutex_try_lock(s)) return EBUSY; pt_fence(); return 0; }
int ns33_pthread_spin_unlock(pthread_spinlock_t *s)
{ if (!s) return EINVAL; pt_fence(); *(volatile int *)&s->lock = 0; return 0; }
int ns33_pthread_spin_destroy(pthread_spinlock_t *s)
{ if (!s) return EINVAL; return s->lock ? EBUSY : 0; }
/* Fork repair only removes pointers to stacks belonging to vanished threads.
   Synchronizers used by the child must be quiescent across fork. */
void pt_extra_fork_child(void)
{
  struct rwstate *r;
  struct barrierstate *b;
  struct reader *owner;
  for (r = rwlocks; r; r = r->next) {
    memset(&r->waiters, 0, sizeof(r->waiters)); r->users = r->writers = 0;
    if (r->writer && r->writer != cthread_self()) r->writer = PT_ENDED_OWNER;
    for (owner = r->readers; owner; owner = owner->next)
      if (owner->thread != cthread_self()) owner->thread = PT_ENDED_OWNER;
  }
  for (b = barriers; b; b = b->next) {
    memset(&b->waiters, 0, sizeof(b->waiters)); b->users = b->arrived = 0;
  }
}

void pt_extra_thread_exit_locked(pthread_t thread)
{
  struct rwstate *r;
  struct reader *owner;
  for (r = rwlocks; r; r = r->next) {
    if (r->writer == thread) r->writer = PT_ENDED_OWNER;
    for (owner = r->readers; owner; owner = owner->next)
      if (owner->thread == thread) owner->thread = PT_ENDED_OWNER;
  }
}
