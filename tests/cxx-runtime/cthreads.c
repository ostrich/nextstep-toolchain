/* Native cthreads ABI foundation for the modern runtime.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <mach/cthreads.h>

static struct mutex lock = MUTEX_INITIALIZER;
static struct condition ready = CONDITION_INITIALIZER;
static int started, release_workers, counter, failures;
static any_t worker(any_t arg)
{
  int index;
  cthread_t self = cthread_self();
  if (!self || self == arg) return (any_t)1;
  mutex_lock(&lock);
  ++started;
  condition_broadcast(&ready);
  while (!release_workers) condition_wait(&ready, &lock);
  mutex_unlock(&lock);
  for (index = 0; index < 1000; ++index) {
    mutex_lock(&lock);
    ++counter;
    mutex_unlock(&lock);
    if (!(index % 37)) cthread_yield();
  }
  return (any_t)0;
}
int main(void)
{
  cthread_t threads[4], self;
  int index;
  cthread_init();
  self = cthread_self();
  if (!self) { puts("cthreads: main identity missing"); return 1; }
  for (index = 0; index < 4; ++index) threads[index] = cthread_fork(worker, self);
  mutex_lock(&lock);
  while (started != 4) condition_wait(&ready, &lock);
  release_workers = 1;
  condition_broadcast(&ready);
  mutex_unlock(&lock);
  for (index = 0; index < 4; ++index)
    if (!threads[index] || cthread_join(threads[index])) ++failures;
  if (counter != 4000) ++failures;
  printf("cthreads: %d increments, %d failures\n", counter, failures);
  return failures != 0;
}
