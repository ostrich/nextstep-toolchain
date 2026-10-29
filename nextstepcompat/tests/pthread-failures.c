/* Link with a private, port-allocation-fault build of pthread-subset.c.
   No fault injection entry is installed in the library. SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"fault FAIL %d: %s\n",__LINE__,#x); exit(2); } } while (0)
#define OK(x) CHECK((x)==0)
static struct mutex injection_lock = MUTEX_INITIALIZER;
static pthread_t fail_thread;
static unsigned remaining, fail_memory, fail_calloc;
static unsigned live_allocations;
static void *allocations[32];
extern void *real_malloc(size_t) __asm__("_malloc");
extern void *real_calloc(size_t, size_t) __asm__("_calloc");
extern void real_free(void *) __asm__("_free");
extern kern_return_t real_port_allocate(task_t, port_t *) __asm__("_port_allocate");
static void configure_failure(unsigned count)
{
  mutex_lock(&injection_lock); fail_thread = pthread_self(); remaining = count;
  mutex_unlock(&injection_lock);
}
kern_return_t pt_test_port_allocate(task_t task, port_t *port)
{
  int fail;
  mutex_lock(&injection_lock);
  fail = remaining && fail_thread == cthread_self();
  if (fail) --remaining;
  mutex_unlock(&injection_lock);
  return fail ? KERN_RESOURCE_SHORTAGE : real_port_allocate(task, port);
}
static void configure_memory(unsigned mallocs, unsigned callocs)
{
  mutex_lock(&injection_lock); fail_thread = pthread_self();
  fail_memory = mallocs; fail_calloc = callocs; mutex_unlock(&injection_lock);
}
void *pt_test_malloc(size_t n)
{
  void *p;
  unsigned i;
  mutex_lock(&injection_lock);
  if (fail_memory && fail_thread == cthread_self()) {
    --fail_memory; mutex_unlock(&injection_lock); return 0;
  }
  p = real_malloc(n);
  if (p) {
    for (i = 0; i < 32 && allocations[i]; ++i) {}
    CHECK(i < 32); allocations[i] = p; ++live_allocations;
  }
  mutex_unlock(&injection_lock); return p;
}
void *pt_test_calloc(size_t n, size_t size)
{
  mutex_lock(&injection_lock);
  if (fail_calloc && fail_thread == cthread_self()) {
    --fail_calloc; mutex_unlock(&injection_lock); return 0;
  }
  mutex_unlock(&injection_lock); return real_calloc(n, size);
}
void pt_test_free(void *p)
{
  unsigned i;
  mutex_lock(&injection_lock);
  for (i = 0; i < 32; ++i) if (allocations[i] == p && p) {
    allocations[i] = 0; --live_allocations; break;
  }
  mutex_unlock(&injection_lock); real_free(p);
}
/* Link-only replacement for native fork. Simulate a global errno race while
   preserving the correct per-Cproc syscall failure. Not installed anywhere. */
static int fork_callbacks;
pid_t pt_test_native_fork(void) __asm__("_fork");
pid_t pt_test_native_fork(void)
{ cthread_set_errno_self(EAGAIN); errno = EINTR; return -1; }
static void prepare_fork(void) { fork_callbacks = fork_callbacks * 10 + 1; }
static void parent_fork(void) { fork_callbacks = fork_callbacks * 10 + 2; errno = EIO; }
static void child_fork(void) { fork_callbacks = 99; }
static int initialized;
static void initialize(void) { ++initialized; }
static void *identity(void *p) { return p; }
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
static pthread_barrier_t barrier;
static pthread_rwlock_t rw = PTHREAD_RWLOCK_INITIALIZER;
static void *contended(void *unused)
{
  struct timespec past = {0,0};
  (void)unused;
  configure_failure(1);
  CHECK(pthread_mutex_timedlock(&mutex, &past) == EAGAIN);
  configure_failure(1);
  CHECK(pthread_rwlock_timedrdlock(&rw, &past) == EAGAIN);
  configure_failure(1);
  CHECK(pthread_rwlock_timedwrlock(&rw, &past) == EAGAIN);
  return 0;
}
static pthread_t target;
static struct mutex native_lock = MUTEX_INITIALIZER;
static struct condition native_cond = CONDITION_INITIALIZER;
static int ready, release;
static void *wait_native(void *arg)
{
  mutex_lock(&native_lock); ready = 1; condition_signal(&native_cond);
  while (!release) condition_wait(&native_cond, &native_lock);
  mutex_unlock(&native_lock); return arg;
}
int main(void)
{
  struct timespec past = {0,0};
  pthread_t worker;
  void *result;
  unsigned i;
  pthread_once_t once = PTHREAD_ONCE_INIT;
  alarm(60);
  configure_memory(1, 0);
  CHECK(pthread_once(&once, initialize) == ENOMEM && initialized == 0);
  OK(pthread_once(&once, initialize)); CHECK(initialized == 1 && live_allocations == 0);
  for (i = 0; i < 256; ++i) {
    pthread_once_t local_once = PTHREAD_ONCE_INIT;
    OK(pthread_once(&local_once, initialize));
    CHECK(live_allocations == 0);
  }
  CHECK(initialized == 257);
  worker = (pthread_t)17; configure_memory(0, 1);
  CHECK(pthread_create(&worker, 0, identity, 0) == EAGAIN && worker == (pthread_t)17);
  configure_failure(1);
  CHECK(pthread_create(&worker, 0, identity, 0) == EAGAIN && worker == (pthread_t)17);
  OK(pthread_mutex_lock(&mutex));
  configure_failure(1);
  CHECK(pthread_cond_timedwait(&cond, &mutex, &past) == EAGAIN);
  CHECK(pthread_mutex_trylock(&mutex) == EBUSY);
  OK(pthread_mutex_unlock(&mutex));
  OK(pthread_cond_destroy(&cond));
  OK(pthread_mutex_lock(&mutex)); OK(pthread_rwlock_wrlock(&rw));
  OK(pthread_create(&worker, 0, contended, 0)); OK(pthread_join(worker, 0));
  OK(pthread_mutex_unlock(&mutex)); OK(pthread_rwlock_unlock(&rw));
  OK(pthread_rwlock_destroy(&rw)); OK(pthread_mutex_destroy(&mutex));
  OK(pthread_barrier_init(&barrier, 0, 1));
  configure_failure(1); CHECK(pthread_barrier_wait(&barrier) == EAGAIN);
  CHECK(pthread_barrier_wait(&barrier) == PTHREAD_BARRIER_SERIAL_THREAD);
  OK(pthread_barrier_destroy(&barrier));
  OK(pthread_create(&target, 0, wait_native, (void *)42));
  mutex_lock(&native_lock); while (!ready) condition_wait(&native_cond, &native_lock); mutex_unlock(&native_lock);
  configure_failure(1); CHECK(pthread_join(target, &result) == EAGAIN);
  mutex_lock(&native_lock); release = 1; condition_signal(&native_cond); mutex_unlock(&native_lock);
  OK(pthread_join(target, &result)); CHECK(result == (void *)42);
  CHECK(live_allocations == 0);
  OK(pthread_atfork(prepare_fork, parent_fork, child_fork));
  CHECK(fork() == -1 && errno == EAGAIN && cthread_errno() == EAGAIN && fork_callbacks == 12);
  OK(pthread_create(&worker, 0, identity, (void *)71));
  OK(pthread_join(worker, &result)); CHECK(result == (void *)71);
  puts("PASS fork failure callbacks and per-Cproc error preservation");
  puts("PASS pthread allocation failures: ownership, join claim, queue and barrier rollback");
  return 0;
}
