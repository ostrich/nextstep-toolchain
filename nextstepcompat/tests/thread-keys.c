/* Key isolation, native recycling and destructor lifecycle. SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
static pthread_key_t key, limit_key;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned destructors, limit_calls, errors;
struct state { unsigned number, calls; };
static void destroy(void *opaque)
{
  struct state *s = opaque;
  pthread_mutex_lock(&lock);
  if (pthread_getspecific(key)) ++errors;
  ++destructors;
  ++s->calls;
  pthread_mutex_unlock(&lock);
  if (s->calls < 3 && pthread_setspecific(key, s)) {
    pthread_mutex_lock(&lock); ++errors; pthread_mutex_unlock(&lock);
  }
}
static void repeat_destructor(void *value)
{
  pthread_mutex_lock(&lock);
  ++limit_calls;
  pthread_mutex_unlock(&lock);
  if (pthread_setspecific(limit_key, value)) {
    pthread_mutex_lock(&lock); ++errors; pthread_mutex_unlock(&lock);
  }
}
static void *worker(void *opaque)
{
  struct state *s = opaque;
  void *old_data = cthread_data(pthread_self());
  if (pthread_getspecific(key) || pthread_getspecific(limit_key) ||
      pthread_setspecific(limit_key, s) || pthread_setspecific(key, s) ||
      pthread_getspecific(key) != s ||
      cthread_data(pthread_self()) != old_data) return (void *)1;
  cthread_yield();
  if (pthread_getspecific(key) != s) return (void *)2;
  if (s->number & 1) pthread_exit(s);
  return s;
}
static any_t foreign(any_t unused)
{
  int result;
  (void)unused;
  result = pthread_setspecific(key, (void *)1);
  return (any_t)(long)(result != ENOTSUP || pthread_getspecific(key) != 0);
}
int main(void)
{
  struct state states[68];
  pthread_t threads[4];
  pthread_key_t deleted, all[PTHREAD_KEYS_MAX];
  pthread_attr_t attr = {0};
  void *result;
  unsigned i, j;
  int main_value;
  alarm(45);
  if (pthread_key_create(&key, destroy) ||
      pthread_key_create(&limit_key, repeat_destructor) ||
      pthread_setspecific(key, &main_value)) return 1;
  if (pthread_create(0, 0, worker, 0) != EINVAL ||
      pthread_create(&threads[0], &attr, worker, 0) != EINVAL ||
      pthread_join(pthread_self(), 0) != EDEADLK) return 2;
  if (pthread_key_create(&deleted, 0) || pthread_setspecific(deleted, &main_value) ||
      pthread_key_delete(deleted) || pthread_getspecific(deleted) ||
      pthread_setspecific(deleted, 0) != EINVAL || pthread_key_delete(deleted) != EINVAL) return 3;
  for (i = 0; i < PTHREAD_KEYS_MAX-2; ++i)
    if (pthread_key_create(&all[i], 0) || all[i] == deleted) return 4;
  if (pthread_key_create(&all[PTHREAD_KEYS_MAX-2], 0) != EAGAIN) return 5;
  for (i = 0; i < PTHREAD_KEYS_MAX-2; ++i) if (pthread_key_delete(all[i])) return 6;
  for (i = 0; i < 64; ++i) {
    states[i].number = i; states[i].calls = 0;
    if (pthread_create(&threads[0], 0, worker, &states[i]) ||
        pthread_join(threads[0], &result) || result != &states[i] || states[i].calls != 3) return 7;
  }
  for (i = 0; i < 4; ++i) {
    j = 64+i; states[j].number = j; states[j].calls = 0;
    if (pthread_create(&threads[i], 0, worker, &states[j])) return 8;
  }
  for (i = 0; i < 4; ++i)
    if (pthread_join(threads[i], &result) || result != &states[64+i] || states[64+i].calls != 3) return 9;
  if (cthread_join(cthread_fork(foreign, 0))) return 10;
  if (errors || destructors != 204 || limit_calls != 272 || pthread_getspecific(key) != &main_value) return 11;
  if (pthread_setspecific(key, 0) || pthread_key_delete(key) || pthread_key_delete(limit_key)) return 12;
  puts("PASS thread keys: 68 managed threads, 476 destructor calls, iteration limit, exit/return, isolation, key reuse/exhaustion, native-thread boundary");
  return 0;
}
