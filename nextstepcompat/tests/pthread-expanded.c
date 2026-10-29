/* Behavioral and race regressions for the documented threading contract.
   SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <fcntl.h>
_Static_assert(sizeof(pthread_mutex_t) == 8, "original mutex ABI");
_Static_assert(sizeof(pthread_cond_t) == 16, "original condition ABI");
_Static_assert(sizeof(pthread_once_t) == 12, "original once ABI");
_Static_assert(sizeof(pthread_attr_t) == 4, "original attribute ABI");
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); exit(2); } } while (0)
#define OK(x) CHECK((x) == 0)
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static pthread_cond_t event = PTHREAD_COND_INITIALIZER;
static int ready, release_gate, exited, cleanup_order, destructor_order;
static pthread_key_t key;
static void deadline_from_timeval(struct timespec *t, const struct timeval *now, long us)
{
  t->tv_sec = now->tv_sec + us / 1000000;
  t->tv_nsec = now->tv_usec * 1000 + (us % 1000000) * 1000;
  if (t->tv_nsec >= 1000000000) { ++t->tv_sec; t->tv_nsec -= 1000000000; }
  if (t->tv_nsec < 0) { --t->tv_sec; t->tv_nsec += 1000000000; }
}
static void deadline(struct timespec *t, long us)
{
  struct timeval now;
  CHECK(gettimeofday(&now, 0) == 0);
  deadline_from_timeval(t, &now, us);
}
static void deadline_arithmetic(void)
{
  struct timespec t;
  struct timeval now = {10,50000};
  deadline_from_timeval(&t, &now, -100000);
  CHECK(t.tv_sec == 9 && t.tv_nsec == 950000000);
  now.tv_usec = 950000;
  deadline_from_timeval(&t, &now, 100000);
  CHECK(t.tv_sec == 11 && t.tv_nsec == 50000000);
  now.tv_usec = 0;
  deadline_from_timeval(&t, &now, -1000000);
  CHECK(t.tv_sec == 9 && t.tv_nsec == 0);
  puts("PASS deadline test-helper normalization");
}
static void *identity(void *value)
{ CHECK(pthread_self() != 0); return value; }
static void just_unlock(void *arg) { OK(pthread_mutex_unlock(arg)); }
static void *gated(void *value)
{
  OK(pthread_mutex_lock(&lock));
  pthread_cleanup_push(just_unlock, &lock);
  ++ready; OK(pthread_cond_broadcast(&changed));
  while (!release_gate) OK(pthread_cond_wait(&changed, &lock));
  pthread_cleanup_pop(1);
  return value;
}
static void wait_ready(int n)
{
  OK(pthread_mutex_lock(&lock));
  while (ready < n) OK(pthread_cond_wait(&changed, &lock));
  OK(pthread_mutex_unlock(&lock));
}
static void open_gate(void)
{ OK(pthread_mutex_lock(&lock)); release_gate = 1; OK(pthread_cond_broadcast(&changed)); OK(pthread_mutex_unlock(&lock)); }
static void attributes(void)
{
  pthread_attr_t a;
  pthread_mutexattr_t m;
  pthread_condattr_t c;
  pthread_rwlockattr_t rw;
  pthread_barrierattr_t b;
  struct sched_param param;
  pthread_t thread;
  int n;
  void *result;
  size_t size;
  OK(pthread_attr_init(&a));
  OK(pthread_attr_getdetachstate(&a, &n)); CHECK(n == PTHREAD_CREATE_JOINABLE);
  OK(pthread_attr_setdetachstate(&a, PTHREAD_CREATE_JOINABLE));
  cthread_set_limit(1);
  CHECK(pthread_create(&thread, &a, identity, 0) == ENOTSUP);
  cthread_set_limit(0);
  CHECK(pthread_attr_setdetachstate(&a, 1234) == EINVAL);
  OK(pthread_attr_getinheritsched(&a, &n)); CHECK(n == PTHREAD_INHERIT_SCHED);
  OK(pthread_attr_setinheritsched(&a, PTHREAD_EXPLICIT_SCHED));
  OK(pthread_attr_getscope(&a, &n)); CHECK(n == PTHREAD_SCOPE_SYSTEM);
  CHECK(pthread_attr_setscope(&a, PTHREAD_SCOPE_PROCESS) == ENOTSUP);
  OK(pthread_attr_getschedpolicy(&a, &n)); CHECK(n == SCHED_OTHER);
  CHECK(pthread_attr_setschedpolicy(&a, SCHED_FIFO) == ENOTSUP);
  OK(pthread_attr_getschedparam(&a, &param)); CHECK(param.sched_priority == 0);
  OK(pthread_attr_setschedparam(&a, &param));
  CHECK(pthread_attr_getstacksize(&a, &size) == ENOTSUP);
  CHECK(pthread_attr_setstacksize(&a, 65536) == ENOTSUP);
  CHECK(pthread_attr_setguardsize(&a, 0) == ENOTSUP);
  OK(pthread_create(&thread, &a, identity, (void *)73));
  OK(pthread_join(thread, &result)); CHECK(result == (void *)73);
  OK(pthread_attr_setinheritsched(&a, PTHREAD_INHERIT_SCHED));
  OK(pthread_attr_destroy(&a)); CHECK(pthread_attr_destroy(&a) == EINVAL);
  OK(pthread_mutexattr_init(&m));
  OK(pthread_mutexattr_gettype(&m, &n)); CHECK(n == PTHREAD_MUTEX_NORMAL);
  CHECK(pthread_mutexattr_setpshared(&m, PTHREAD_PROCESS_SHARED) == ENOTSUP);
  OK(pthread_mutexattr_setrobust(&m, PTHREAD_MUTEX_ROBUST));
  OK(pthread_mutexattr_getrobust(&m, &n)); CHECK(n == PTHREAD_MUTEX_ROBUST);
  OK(pthread_mutexattr_setrobust(&m, PTHREAD_MUTEX_STALLED));
  CHECK(pthread_mutexattr_setprotocol(&m, PTHREAD_PRIO_INHERIT) == ENOTSUP);
  OK(pthread_mutexattr_destroy(&m));
  OK(pthread_condattr_init(&c));
  OK(pthread_condattr_getclock(&c, &n)); CHECK(n == CLOCK_REALTIME);
  CHECK(pthread_condattr_setclock(&c, CLOCK_MONOTONIC) == ENOTSUP);
  OK(pthread_condattr_destroy(&c));
  OK(pthread_rwlockattr_init(&rw));
  CHECK(pthread_rwlockattr_setpshared(&rw, PTHREAD_PROCESS_SHARED) == ENOTSUP);
  OK(pthread_rwlockattr_destroy(&rw));
  OK(pthread_barrierattr_init(&b));
  CHECK(pthread_barrierattr_setpshared(&b, PTHREAD_PROCESS_SHARED) == ENOTSUP);
  OK(pthread_barrierattr_destroy(&b));
  OK(pthread_setconcurrency(7)); CHECK(pthread_getconcurrency() == 7);
  CHECK(pthread_setconcurrency(-1) == EINVAL);
  OK(pthread_setconcurrency(0));
  CHECK(sched_get_priority_min(SCHED_OTHER) == 0);
  CHECK(sched_get_priority_max(SCHED_OTHER) == 0);
  OK(sched_yield());
  OK(pthread_getschedparam(pthread_self(), &n, &param)); CHECK(n == SCHED_OTHER && param.sched_priority == 0);
  OK(pthread_setschedparam(pthread_self(), SCHED_OTHER, &param));
  CHECK(pthread_setschedparam(pthread_self(), SCHED_RR, &param) == ENOTSUP);
  OK(pthread_setschedprio(pthread_self(), 0));
  puts("PASS attributes and explicit unsupported contracts");
}
static void unlock_cleanup(void *arg)
{
  OK(pthread_mutex_unlock(arg));
  cleanup_order = cleanup_order * 10 + 2;
}
static void log_cleanup(void *arg)
{ cleanup_order = cleanup_order * 10 + (int)(long)arg; }
static void dtor(void *value)
{
  CHECK(value == (void *)11);
  CHECK(!pthread_getspecific(key));
  destructor_order = cleanup_order;
  OK(pthread_mutex_lock(&lock)); ++exited; OK(pthread_cond_broadcast(&changed)); OK(pthread_mutex_unlock(&lock));
}
static void *cancel_condition(void *arg)
{
  (void)arg;
  OK(pthread_setspecific(key, (void *)11));
  OK(pthread_mutex_lock(&lock));
  pthread_cleanup_push(log_cleanup, (void *)1);
  pthread_cleanup_push(unlock_cleanup, &lock);
  ++ready; OK(pthread_cond_broadcast(&changed));
  for (;;) OK(pthread_cond_wait(&changed, &lock));
  pthread_cleanup_pop(0);
  pthread_cleanup_pop(0);
  return 0;
}
static void cancellation(void)
{
  pthread_t t;
  void *result;
  int old = 123;
  ready = exited = cleanup_order = destructor_order = 0;
  OK(pthread_key_create(&key, dtor));
  CHECK(pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, &old) == ENOTSUP);
  CHECK(old == 123);
  OK(pthread_setcanceltype(PTHREAD_CANCEL_DEFERRED, &old)); CHECK(old == PTHREAD_CANCEL_DEFERRED);
  OK(pthread_create(&t, 0, cancel_condition, 0));
  wait_ready(1);
  { int policy; struct sched_param p;
    OK(pthread_getschedparam(t, &policy, &p)); CHECK(policy == SCHED_OTHER && p.sched_priority == 0);
    OK(pthread_setschedparam(t, policy, &p)); }
  OK(pthread_cancel(t)); OK(pthread_join(t, &result));
  CHECK(result == PTHREAD_CANCELED && cleanup_order == 21 && destructor_order == 21 && exited == 1);
  OK(pthread_mutex_trylock(&lock)); OK(pthread_mutex_unlock(&lock));
  OK(pthread_key_delete(key));
  puts("PASS condition cancellation, mutex reacquisition, LIFO cleanup and TLS order");
}
static void *disabled_worker(void *unused)
{
  int old;
  (void)unused;
  OK(pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, &old)); CHECK(old == PTHREAD_CANCEL_ENABLE);
  gated(0);
  OK(pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, &old)); CHECK(old == PTHREAD_CANCEL_DISABLE);
  OK(pthread_mutex_lock(&lock)); ++exited; OK(pthread_mutex_unlock(&lock));
  pthread_testcancel();
  return (void *)1;
}
static void cancellation_state(void)
{
  pthread_t t;
  void *result;
  ready = release_gate = exited = 0;
  OK(pthread_create(&t, 0, disabled_worker, 0)); wait_ready(1);
  OK(pthread_cancel(t)); open_gate(); OK(pthread_join(t, &result));
  CHECK(result == PTHREAD_CANCELED && exited == 1);
  puts("PASS disabled and pending deferred cancellation");
}
static pthread_t join_target;
static void *joiner(void *unused)
{
  (void)unused;
  OK(pthread_mutex_lock(&lock)); ++ready; OK(pthread_cond_broadcast(&changed)); OK(pthread_mutex_unlock(&lock));
  OK(pthread_join(join_target, 0));
  return (void *)7;
}
static void *detach_worker(void *unused)
{ (void)unused; OK(pthread_setspecific(key, (void *)11)); return gated(0); }
static void lifecycle(void)
{
  pthread_t t, j;
  pthread_attr_t a;
  void *result;
  unsigned i;
  CHECK(pthread_join(pthread_self(), 0) == EDEADLK);
  ready = release_gate = 0;
  OK(pthread_create(&join_target, 0, gated, (void *)99)); wait_ready(1);
  OK(pthread_create(&j, 0, joiner, 0)); wait_ready(2);
  OK(pthread_cancel(j)); OK(pthread_join(j, &result)); CHECK(result == PTHREAD_CANCELED);
  open_gate(); OK(pthread_join(join_target, &result)); CHECK(result == (void *)99);
  for (i = 0; i < 64; ++i) {
    OK(pthread_create(&t, 0, identity, (void *)(long)(i+1)));
    OK(pthread_join(t, &result)); CHECK(result == (void *)(long)(i+1));
  }
  ready = release_gate = exited = cleanup_order = 0;
  OK(pthread_key_create(&key, dtor));
  OK(pthread_attr_init(&a)); OK(pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED));
  /* Destruction, not a recycled native thread address, witnesses completion. */
  OK(pthread_create(&t, &a, cancel_condition, 0)); wait_ready(1);
  CHECK(pthread_join(t, 0) == EINVAL);
  OK(pthread_cancel(t));
  OK(pthread_mutex_lock(&lock));
  while (!exited) OK(pthread_cond_wait(&changed, &lock));
  OK(pthread_mutex_unlock(&lock));
  OK(pthread_attr_destroy(&a));
  ready = release_gate = exited = 0;
  OK(pthread_create(&t, 0, detach_worker, 0)); wait_ready(1);
  OK(pthread_detach(t)); CHECK(pthread_detach(t) == EINVAL); open_gate();
  OK(pthread_mutex_lock(&lock));
  while (!exited) OK(pthread_cond_wait(&changed, &lock));
  OK(pthread_mutex_unlock(&lock));
  OK(pthread_key_delete(key));
  /* No observation through t after releasing a detached worker. */
  puts("PASS lifecycle, recycling, detach attributes and cancelled join ownership");
}
static pthread_mutex_t typed;
static int expected_lock_error;
static void *lock_contender(void *unused)
{
  struct timespec t;
  (void)unused;
  deadline(&t, 30000);
  CHECK(pthread_mutex_timedlock(&typed, &t) == expected_lock_error);
  CHECK(pthread_mutex_unlock(&typed) == EPERM);
  return 0;
}
static void mutex_tests(void)
{
  pthread_mutexattr_t a;
  pthread_t t;
  struct timespec past = {0, 0}, invalid = {0, 1000000000L};
  OK(pthread_mutexattr_init(&a)); OK(pthread_mutexattr_settype(&a, PTHREAD_MUTEX_RECURSIVE));
  OK(pthread_mutex_init(&typed, &a));
  OK(pthread_mutex_lock(&typed)); OK(pthread_mutex_trylock(&typed));
  CHECK(pthread_mutex_destroy(&typed) == EBUSY);
  OK(pthread_mutex_unlock(&typed));
  expected_lock_error = ETIMEDOUT;
  OK(pthread_create(&t, 0, lock_contender, 0)); OK(pthread_join(t, 0));
  OK(pthread_mutex_unlock(&typed)); OK(pthread_mutex_destroy(&typed));
  OK(pthread_mutexattr_settype(&a, PTHREAD_MUTEX_ERRORCHECK));
  OK(pthread_mutex_init(&typed, &a));
  OK(pthread_mutex_timedlock(&typed, &past)); /* Available mutex beats timeout. */
  CHECK(pthread_mutex_lock(&typed) == EDEADLK);
  CHECK(pthread_mutex_trylock(&typed) == EBUSY);
  OK(pthread_mutex_unlock(&typed));
  OK(pthread_mutex_timedlock(&typed, &invalid)); /* No validation required if acquired. */
  OK(pthread_mutex_unlock(&typed)); OK(pthread_mutex_destroy(&typed));
  OK(pthread_mutexattr_destroy(&a));
  puts("PASS recursive/errorcheck ownership and timed mutexes");
}
static pthread_mutex_t stalled_mutex;
static pthread_rwlock_t stalled_read = PTHREAD_RWLOCK_INITIALIZER;
static pthread_rwlock_t stalled_write = PTHREAD_RWLOCK_INITIALIZER;
static void *abandon_stalled(void *unused)
{
  (void)unused;
  OK(pthread_mutex_lock(&stalled_mutex));
  OK(pthread_rwlock_rdlock(&stalled_read));
  OK(pthread_rwlock_wrlock(&stalled_write));
  return 0;
}
static void *recycled_owner(void *unused)
{
  (void)unused;
  CHECK(pthread_mutex_trylock(&stalled_mutex) == EBUSY);
  CHECK(pthread_rwlock_trywrlock(&stalled_read) == EBUSY);
  CHECK(pthread_rwlock_trywrlock(&stalled_write) == EBUSY);
  CHECK(pthread_rwlock_unlock(&stalled_read) == EPERM);
  CHECK(pthread_rwlock_unlock(&stalled_write) == EPERM);
  return 0;
}
static void stalled_owner_test(void)
{
  pid_t pid = fork();
  int status;
  if (pid < 0) exit(2);
  if (!pid) {
    pthread_t t;
    pthread_mutexattr_t a;
    alarm(20);
    OK(pthread_mutexattr_init(&a));
    OK(pthread_mutexattr_settype(&a, PTHREAD_MUTEX_RECURSIVE));
    OK(pthread_mutex_init(&stalled_mutex, &a));
    OK(pthread_create(&t, 0, abandon_stalled, 0)); OK(pthread_join(t, 0));
    OK(pthread_create(&t, 0, recycled_owner, 0)); OK(pthread_join(t, 0));
    /* These intentionally stalled objects cannot be destroyed or reused. */
    _exit(0);
  }
  CHECK(wait(&status) == pid && WIFEXITED(status) && !WEXITSTATUS(status));
  puts("PASS terminated ownership is not inherited through native handle recycling");
}
static pthread_cond_t robust_condition = PTHREAD_COND_INITIALIZER;
static void *abandon_mutex(void *unused)
{ (void)unused; OK(pthread_mutex_lock(&typed)); return 0; }
static void *robust_waiter(void *unused)
{
  int error;
  (void)unused;
  OK(pthread_mutex_lock(&typed));
  OK(pthread_mutex_lock(&lock)); ++ready; OK(pthread_cond_signal(&changed)); OK(pthread_mutex_unlock(&lock));
  error = pthread_cond_wait(&robust_condition, &typed);
  CHECK(error == EOWNERDEAD);
  OK(pthread_mutex_consistent(&typed)); OK(pthread_mutex_unlock(&typed)); return 0;
}
static void *abandon_after_signal(void *unused)
{
  (void)unused; OK(pthread_mutex_lock(&typed));
  OK(pthread_cond_signal(&robust_condition)); return 0;
}
static void robust_tests(void)
{
  pthread_mutexattr_t a;
  pthread_t t, waiter;
  OK(pthread_mutexattr_init(&a)); OK(pthread_mutexattr_setrobust(&a, PTHREAD_MUTEX_ROBUST));
  OK(pthread_mutex_init(&typed, &a));
  OK(pthread_create(&t, 0, abandon_mutex, 0)); OK(pthread_join(t, 0));
  CHECK(pthread_mutex_trylock(&typed) == EOWNERDEAD);
  OK(pthread_mutex_consistent(&typed)); OK(pthread_mutex_unlock(&typed));
  OK(pthread_mutex_lock(&typed)); OK(pthread_mutex_unlock(&typed));
  OK(pthread_create(&t, 0, abandon_mutex, 0)); OK(pthread_join(t, 0));
  CHECK(pthread_mutex_lock(&typed) == EOWNERDEAD);
  OK(pthread_mutex_unlock(&typed));
  CHECK(pthread_mutex_lock(&typed) == ENOTRECOVERABLE);
  CHECK(pthread_mutex_consistent(&typed) == EINVAL);
  OK(pthread_mutex_destroy(&typed));
  OK(pthread_mutex_init(&typed, &a)); ready = 0;
  OK(pthread_create(&waiter, 0, robust_waiter, 0)); wait_ready(1);
  OK(pthread_create(&t, 0, abandon_after_signal, 0));
  OK(pthread_join(t, 0)); OK(pthread_join(waiter, 0));
  OK(pthread_mutex_destroy(&typed)); OK(pthread_cond_destroy(&robust_condition));
  OK(pthread_mutexattr_destroy(&a));
  puts("PASS robust owner death, recovery, unrecoverable state and condition reacquisition");
}
static void timed_conditions(void)
{
  struct timespec t, now, invalid = {0, -1};
  pthread_cond_t c = PTHREAD_COND_INITIALIZER;
  unsigned i;
  OK(pthread_mutex_lock(&lock));
  CHECK(pthread_cond_timedwait(&c, &lock, &invalid) == EINVAL);
  for (i = 0; i < 16; ++i) {
    deadline(&t, i ? -100000 : 30000);
    CHECK(pthread_cond_timedwait(&c, &lock, &t) == ETIMEDOUT);
    deadline(&now, 0);
    CHECK(now.tv_sec > t.tv_sec || (now.tv_sec == t.tv_sec && now.tv_nsec >= t.tv_nsec));
  }
  OK(pthread_mutex_unlock(&lock)); OK(pthread_cond_destroy(&c));
  puts("PASS absolute condition deadlines and no early timeout");
}
static pthread_mutex_t binding_a = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t binding_b = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t binding_condition = PTHREAD_COND_INITIALIZER;
static void *binding_waiter(void *unused)
{
  (void)unused;
  OK(pthread_mutex_lock(&binding_a));
  OK(pthread_mutex_lock(&lock)); ++ready; OK(pthread_cond_signal(&changed)); OK(pthread_mutex_unlock(&lock));
  OK(pthread_cond_wait(&binding_condition, &binding_a));
  OK(pthread_mutex_unlock(&binding_a)); return 0;
}
static void binding_test(void)
{
  pthread_t t;
  struct timespec past = {0,0};
  ready = 0;
  OK(pthread_create(&t, 0, binding_waiter, 0)); wait_ready(1);
  OK(pthread_mutex_lock(&binding_a));
  OK(pthread_cond_signal(&binding_condition));
  /* The old waiter is unblocked but cannot reacquire binding_a yet. */
  OK(pthread_mutex_lock(&binding_b));
  CHECK(pthread_cond_timedwait(&binding_condition, &binding_b, &past) == ETIMEDOUT);
  OK(pthread_mutex_unlock(&binding_b)); OK(pthread_mutex_unlock(&binding_a));
  OK(pthread_join(t, 0));
  OK(pthread_cond_destroy(&binding_condition));
  OK(pthread_mutex_destroy(&binding_a)); OK(pthread_mutex_destroy(&binding_b));
  puts("PASS dynamic condition binding after notification");
}
static pthread_once_t once = PTHREAD_ONCE_INIT;
static int once_calls;
static void initialize_once(void)
{
  ++once_calls;
  if (once_calls == 1) gated(0);
}
static void *once_worker(void *unused)
{ (void)unused; OK(pthread_once(&once, initialize_once)); return 0; }
static void once_tests(void)
{
  pthread_t t;
  void *result;
  pid_t pid;
  int status;
  ready = release_gate = once_calls = 0;
  OK(pthread_create(&t, 0, once_worker, 0)); wait_ready(1);
  pid = fork(); CHECK(pid >= 0);
  if (!pid) { alarm(15); OK(pthread_once(&once, initialize_once)); CHECK(once_calls == 2); _exit(0); }
  CHECK(wait(&status) == pid && WIFEXITED(status) && !WEXITSTATUS(status));
  OK(pthread_cancel(t)); OK(pthread_join(t, &result)); CHECK(result == PTHREAD_CANCELED);

  OK(pthread_once(&once, initialize_once)); CHECK(once_calls == 2);
  puts("PASS once rollback after cancellation and fork with active initializer");
}
static pthread_rwlock_t rw = PTHREAD_RWLOCK_INITIALIZER;
static pthread_barrier_t barrier;
static pthread_spinlock_t spin;
static unsigned shared_value, spin_count, serial_count, phase_values[4];
static void *parallel_worker(void *opaque)
{
  unsigned id = (unsigned)(long)opaque, round;
  for (round = 0; round < 128; ++round) {
    int status;
    OK(pthread_rwlock_wrlock(&rw)); ++shared_value; OK(pthread_rwlock_unlock(&rw));
    OK(pthread_rwlock_rdlock(&rw));
    OK(pthread_rwlock_rdlock(&rw));
    CHECK(shared_value != 0);
    OK(pthread_rwlock_unlock(&rw)); OK(pthread_rwlock_unlock(&rw));
    OK(pthread_spin_lock(&spin)); ++spin_count; OK(pthread_spin_unlock(&spin));
    phase_values[id] = round + 1;
    status = pthread_barrier_wait(&barrier);
    CHECK(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
    if (status == PTHREAD_BARRIER_SERIAL_THREAD) {
      unsigned i;
      for (i = 0; i < 4; ++i) CHECK(phase_values[i] == round + 1);
      ++serial_count;
    }
    status = pthread_barrier_wait(&barrier);
    CHECK(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
  }
  return 0;
}
static void *rw_contender(void *unused)
{
  struct timespec t;
  (void)unused;
  deadline(&t, 30000); CHECK(pthread_rwlock_timedrdlock(&rw, &t) == ETIMEDOUT);
  deadline(&t, 30000); CHECK(pthread_rwlock_timedwrlock(&rw, &t) == ETIMEDOUT);
  return 0;
}
static void parallel_tests(void)
{
  pthread_t t[4];
  unsigned i;
  struct timespec past = {0, 0};
  OK(pthread_barrier_init(&barrier, 0, 4)); OK(pthread_spin_init(&spin, PTHREAD_PROCESS_PRIVATE));
  for (i = 0; i < 4; ++i) OK(pthread_create(&t[i], 0, parallel_worker, (void *)(long)i));
  for (i = 0; i < 4; ++i) OK(pthread_join(t[i], 0));
  CHECK(shared_value == 512 && spin_count == 512 && serial_count == 128);
  OK(pthread_rwlock_timedwrlock(&rw, &past));
  CHECK(pthread_rwlock_tryrdlock(&rw) == EBUSY);
  CHECK(pthread_rwlock_destroy(&rw) == EBUSY);
  OK(pthread_create(&t[0], 0, rw_contender, 0)); OK(pthread_join(t[0], 0));
  OK(pthread_rwlock_unlock(&rw));
  OK(pthread_rwlock_destroy(&rw)); OK(pthread_barrier_destroy(&barrier));
  OK(pthread_spin_trylock(&spin)); CHECK(pthread_spin_trylock(&spin) == EBUSY);
  CHECK(pthread_spin_destroy(&spin) == EBUSY);
  OK(pthread_spin_unlock(&spin)); OK(pthread_spin_destroy(&spin));
  puts("PASS rwlock, spinlock and reusable barrier contention/publication");
}
static void *race_waiter(void *unused)
{
  (void)unused;
  OK(pthread_mutex_lock(&lock));
  pthread_cleanup_push(just_unlock, &lock);
  ++ready; OK(pthread_cond_broadcast(&changed));
  while (!release_gate) OK(pthread_cond_wait(&event, &lock));
  pthread_cleanup_pop(1);
  return 0;
}
static void cancellation_races(void)
{
  unsigned i;
  pthread_t t[2];
  void *value;
  for (i = 0; i < 32; ++i) {
    ready = release_gate = 0;
    OK(pthread_create(&t[0], 0, race_waiter, 0)); wait_ready(1);
    OK(pthread_create(&t[1], 0, race_waiter, 0)); wait_ready(2);
    OK(pthread_mutex_lock(&lock));
    release_gate = 1;
    OK(pthread_cond_signal(&event));
    OK(pthread_cancel(t[0]));
    OK(pthread_mutex_unlock(&lock));
    OK(pthread_join(t[0], &value)); CHECK(value == PTHREAD_CANCELED);
    OK(pthread_join(t[1], &value)); CHECK(value == 0);
  }
  puts("PASS 32 cancellation/signal races with notification replacement");
}
static unsigned fork_order;
static void prep1(void) { fork_order = fork_order * 10 + 1; }
static int extra_registered;
static void prep3(void) { fork_order = fork_order * 10 + 7; }
static void parent3(void) { fork_order = fork_order * 10 + 8; }
static void child3(void) { fork_order = fork_order * 10 + 9; }
static void prep2(void)
{
  fork_order = fork_order * 10 + 2;
  if (!extra_registered) {
    OK(pthread_atfork(prep3, parent3, child3)); extra_registered = 1;
  }
}
static void parent1(void) { fork_order = fork_order * 10 + 3; }
static void parent2(void) { fork_order = fork_order * 10 + 4; }
static void child1(void) { fork_order = fork_order * 10 + 5; }
static void child2(void) { fork_order = fork_order * 10 + 6; }
static void fork_tests(void)
{
  pid_t pid;
  int status;
  pthread_t t;
  void *result;
  OK(pthread_atfork(prep1, parent1, child1)); OK(pthread_atfork(prep2, parent2, child2));
  OK(pthread_key_create(&key, 0)); OK(pthread_setspecific(key, (void *)87));
  fork_order = 0; pid = fork(); CHECK(pid >= 0);
  if (!pid) {
    alarm(15);
    CHECK(fork_order == 2156 && pthread_getspecific(key) == (void *)87);
    OK(pthread_create(&t, 0, identity, (void *)88)); OK(pthread_join(t, &result));
    CHECK(result == (void *)88); _exit(0);
  }
  CHECK(fork_order == 2134);
  CHECK(wait(&status) == pid && WIFEXITED(status) && !WEXITSTATUS(status));
  fork_order = 0; pid = fork(); CHECK(pid >= 0);
  if (!pid) { CHECK(fork_order == 721569); _exit(0); }
  CHECK(fork_order == 721348);
  CHECK(wait(&status) == pid && WIFEXITED(status) && !WEXITSTATUS(status));
  CHECK(pthread_getspecific(key) == (void *)87); OK(pthread_key_delete(key));
  puts("PASS native fork integration, handler order, retained TLS and child creation");
}
static void signals(void)
{
  sigset_t set;
  OK(sigemptyset(&set)); OK(sigaddset(&set, SIGUSR1));
  OK(pthread_kill(pthread_self(), 0));
  CHECK(pthread_kill(pthread_self(), SIGUSR1) == ENOTSUP);
  CHECK(pthread_sigmask(SIG_BLOCK, &set, 0) == ENOTSUP);
  puts("PASS signal limitations rejected without changing process masks");
}
int main(void)
{
  alarm(180);
  setvbuf(stdout, 0, _IONBF, 0);
  deadline_arithmetic(); attributes(); mutex_tests(); stalled_owner_test(); robust_tests(); timed_conditions(); binding_test();
  cancellation(); cancellation_state(); lifecycle(); once_tests();
  parallel_tests(); cancellation_races(); fork_tests(); signals();
  puts("PASS expanded pthread suite");
  return 0;
}
