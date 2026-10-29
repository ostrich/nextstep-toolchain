/* C++ linkage, normal RAII and lexical pthread cleanup. SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int order;
struct Guard { ~Guard() { order = order * 10 + 2; } };
static void cleanup(void *) { order = order * 10 + 1; }
static void *worker(void *)
{
  Guard guard;
  if (!pthread_self() || !cthread_self()) std::abort();
  if (pthread_mutex_lock(&lock)) std::abort();
  pthread_cleanup_push(cleanup, 0);
  pthread_cleanup_pop(1);
  if (pthread_mutex_unlock(&lock)) std::abort();
  return reinterpret_cast<void *>(73);
}
int main()
{
  pthread_t t;
  void *result;
  alarm(30);
  if (pthread_create(&t, 0, worker, 0) || pthread_join(t, &result) ||
      result != reinterpret_cast<void *>(73) || order != 12 ||
      pthread_mutex_destroy(&lock)) return 1;
  std::puts("PASS C++ pthread/native linkage, ordinary RAII and lexical cleanup");
  return 0;
}
