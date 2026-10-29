/* Native gthread bridge regressions, independent of libstdc++.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/time.h>
#include <mach/cthreads.h>
#include "gthr-nextstep.h"
static __gthread_mutex_t lock = __GTHREAD_MUTEX_INIT;
static __gthread_cond_t ready = __GTHREAD_COND_INIT;
static __gthread_once_t once = __GTHREAD_ONCE_INIT;
static __gthread_key_t key;
static volatile long double numerator = 1.0L;
static int started, release_workers, counter, destroyed, once_count, failures, checks;
static void check(int okay, const char *name)
{ fprintf(stderr, "CHECK %s\n", name); ++checks; if (!okay) { ++failures; fprintf(stderr, "FAIL %s\n", name); } }
static void once_init(void) { ++once_count; }
struct payload { int pass; void *identity; };
static void destroy(void *value)
{
  struct payload *payload = value;
  __gthread_mutex_lock(&lock);
  ++destroyed;
  __gthread_cond_broadcast(&ready);
  __gthread_mutex_unlock(&lock);
  if (!payload->pass++) __gthread_setspecific(key, payload);
  else free(payload);
}
static void *worker(void *argument)
{
  struct payload *payload = calloc(1, sizeof(*payload));
  int i, error = 0;
  if (!payload) return (void *)0x1020;
  payload->identity = argument;
  cthread_set_data(cthread_self(), argument);
  error |= __gthread_getspecific(key) != 0;
  error |= (__gthread_setspecific(key, payload) != 0) << 1;
  error |= (__gthread_getspecific(key) != payload) << 2;
  error |= (cthread_data(cthread_self()) != argument) << 3;
#if __LDBL_MANT_DIG__ > __DBL_MANT_DIG__
  { volatile double rounded = (double)numerator / 3.0;
    error |= (!(numerator / 3.0L > (long double)rounded)) << 4; }
#endif
  __gthread_once(&once, once_init);
  __gthread_mutex_lock(&lock);
  ++started;
  __gthread_cond_broadcast(&ready);
  while (!release_workers) __gthread_cond_wait(&ready, &lock);
  __gthread_mutex_unlock(&lock);
  for (i = 0; i < 1000; ++i) {
    __gthread_mutex_lock(&lock); ++counter; __gthread_mutex_unlock(&lock);
    if (!(i % 37)) __gthread_yield();
  }
  return error ? (void *)(long)(0x1000 | error) : argument;
}
static __gthread_time_t deadline(void)
{
  struct timeval now;
  __gthread_time_t result;
  gettimeofday(&now, 0);
  result.tv_sec = now.tv_sec;
  result.tv_nsec = now.tv_usec * 1000 + 50000000;
  if (result.tv_nsec >= 1000000000) { ++result.tv_sec; result.tv_nsec -= 1000000000; }
  return result;
}
static void *timed_worker(void *unused)
{
  __gthread_time_t end = deadline();
  (void)unused;
  return (void *)(long)__gthread_mutex_timedlock(&lock, &end);
}
int main(void)
{
  __gthread_t workers[4], timed;
  __gthread_recursive_mutex_t recursive = __GTHREAD_RECURSIVE_MUTEX_INIT;
  __gthread_once_t retry = __GTHREAD_ONCE_INIT;
  __gthread_key_t second;
  __gthread_time_t end;
  void *result;
  int i, marker;
  fprintf(stderr, "STAGE main\n");
  check(__gthread_active_p() && __gthread_self(), "thread identity");
  cthread_set_data(cthread_self(), &marker);
  check(!__gthread_key_create(&key, destroy), "key creation");
  for (i = 0; i < 4; ++i)
    check(!__gthread_create(&workers[i], worker, (void *)(long)(i + 20)), "create");
  __gthread_mutex_lock(&lock);
  while (started != 4) __gthread_cond_wait(&ready, &lock);
  release_workers = 1;
  __gthread_cond_broadcast(&ready);
  __gthread_mutex_unlock(&lock);
  for (i = 0; i < 4; ++i) {
    check(!__gthread_join(workers[i], &result), "join");
    if (result != (void *)(long)(i + 20)) fprintf(stderr, "worker error bits: %lx\n", (unsigned long)result);
    check(result == (void *)(long)(i + 20), "worker TLS and return");
  }
  check(counter == 4000, "mutex exclusion");
  check(once_count == 1, "contended once");
  check(destroyed == 8, "TLS destructor retry and cleanup");
  check(!__gthread_getspecific(key), "main TLS isolated");
  check(cthread_data(cthread_self()) == &marker, "native application data preserved");
  __gthread_mutex_lock(&lock);
  end = deadline();
  check(__gthread_cond_timedwait(&ready, &lock, &end) == ETIMEDOUT, "condition deadline");
  check(__gthread_mutex_trylock(&lock) == EBUSY, "wait reacquires mutex");
  check(!__gthread_create(&timed, timed_worker, 0), "timed worker create");
  check(!__gthread_join(timed, &result) && (long)result == ETIMEDOUT, "mutex deadline");
  __gthread_mutex_unlock(&lock);
  check(!__gthread_recursive_mutex_lock(&recursive), "recursive lock");
  check(!__gthread_recursive_mutex_trylock(&recursive), "recursive relock");
  check(!__gthread_recursive_mutex_unlock(&recursive) &&
        !__gthread_recursive_mutex_unlock(&recursive), "recursive release");
  check(!__gthread_recursive_mutex_destroy(&recursive), "recursive destroy");
  check(__nextstep_gthread_once_enter(&retry) == 1, "once enter");
  __nextstep_gthread_once_finish(&retry, 0);
  check(__nextstep_gthread_once_enter(&retry) == 1, "once retry");
  __nextstep_gthread_once_finish(&retry, 1);
  check(__nextstep_gthread_once_enter(&retry) == 0, "once completed");
  check(!__gthread_key_delete(key), "key delete");
  check(!__gthread_key_create(&second, 0) && second != key, "no stale key reuse");
  check(__gthread_setspecific(key, &marker) == EINVAL, "deleted key rejected");
  check(!__gthread_key_delete(second), "second key delete");
  check(!__gthread_cond_destroy(&ready), "condition destroy");
  printf("gthread: %d checks, %d increments, %d destructors, %d failures\n",
         checks, counter, destroyed, failures);
  return failures != 0;
}
