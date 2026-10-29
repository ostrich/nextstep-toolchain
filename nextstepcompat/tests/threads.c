/* Native concurrency and quiescent-fork tests. SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <endian.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static unsigned count;
static int initialized, published[32];
static pthread_t main_thread;
static void initialize(void)
{
  int i;
  ++initialized;
  for (i = 0; i < 32; ++i) { published[i] = i * 7; cthread_yield(); }
}
static any_t worker(any_t unused)
{
  int i, j;
  pthread_t self = pthread_self();
  (void)unused;
  if (!self || pthread_equal(self,main_thread) || !pthread_equal(self,pthread_self())) return (any_t)1;
  for (i = 0; i < 2000; ++i) {
    if (pthread_once(&once,initialize)) return (any_t)2;
    for (j = 0; j < 32; ++j) if (published[j] != j * 7) return (any_t)3;
    if (pthread_mutex_lock(&lock)) return (any_t)4;
    ++count;
    if (pthread_mutex_unlock(&lock)) return (any_t)5;
    if (!(i % 31)) cthread_yield();
  }
  return 0;
}
static pthread_cond_t gate = PTHREAD_COND_INITIALIZER;
static pthread_cond_t progress = PTHREAD_COND_INITIALIZER;
static unsigned ready, generation, acknowledged;
static any_t condition_worker(any_t unused)
{
  unsigned round;
  (void)unused;
  if (!pthread_self()->func) return (any_t)1;
  pthread_mutex_lock(&lock);
  ++ready;
  pthread_cond_signal(&progress);
  for (round = 1; round <= 100; ++round) {
    while (generation < round)
      if (pthread_cond_wait(&gate, &lock)) return (any_t)2;
    ++acknowledged;
    pthread_cond_signal(&progress);
  }
  pthread_mutex_unlock(&lock);
  return 0;
}
static int condition_tests(void)
{
  cthread_t threads[4];
  pthread_cond_t dynamic;
  pthread_condattr_t unsupported = {0};
  unsigned i, round;
  if (pthread_self()->func) return 1;
  if (pthread_cond_init(&dynamic, &unsupported) != EINVAL ||
      pthread_cond_init(&dynamic, 0) || pthread_cond_destroy(&dynamic)) return 2;
  if (pthread_cond_wait(0, &lock) != EINVAL ||
      pthread_cond_wait(&gate, 0) != EINVAL ||
      pthread_cond_signal(0) != EINVAL || pthread_cond_broadcast(0) != EINVAL ||
      pthread_cond_destroy(0) != EINVAL) return 3;
  for (i = 0; i < 4; ++i)
    if (!(threads[i] = cthread_fork(condition_worker, 0))) return 4;
  pthread_mutex_lock(&lock);
  while (ready < 4) pthread_cond_wait(&progress, &lock);
  /* Every worker queued before releasing lock in its first condition_wait. */
  if (pthread_cond_destroy(&gate) != EBUSY) return 5;
  for (round = 1; round <= 100; ++round) {
    generation = round;
    pthread_cond_broadcast(&gate);
    while (acknowledged < round * 4) pthread_cond_wait(&progress, &lock);
  }
  pthread_mutex_unlock(&lock);
  for (i = 0; i < 4; ++i) if (cthread_join(threads[i])) return 6;
  if (pthread_cond_destroy(&gate) || pthread_cond_destroy(&progress)) return 7;
  return 0;
}
static int byte_order(void)
{
  uint16_t a = htobe16(0x1234), b = htole16(0x1234);
  uint32_t c = htobe32(UINT32_C(0x12345678)), d = htole32(UINT32_C(0x12345678));
  uint64_t e = htobe64(UINT64_C(0x123456789abcdef0));
  uint64_t f = htole64(UINT64_C(0x123456789abcdef0));
  unsigned i = 1;
  if (memcmp(&a,"\x12\x34",2) || memcmp(&b,"\x34\x12",2)) return 1;
  if (memcmp(&c,"\x12\x34\x56\x78",4) || memcmp(&d,"\x78\x56\x34\x12",4)) return 2;
  if (memcmp(&e,"\x12\x34\x56\x78\x9a\xbc\xde\xf0",8) || memcmp(&f,"\xf0\xde\xbc\x9a\x78\x56\x34\x12",8)) return 3;
  if (be16toh(a)!=0x1234 || le16toh(b)!=0x1234 || be32toh(c)!=0x12345678 || le32toh(d)!=0x12345678) return 4;
  if (be64toh(e)!=UINT64_C(0x123456789abcdef0) || le64toh(f)!=UINT64_C(0x123456789abcdef0)) return 5;
  (void)htobe64(i++); if (i != 2) return 6;
  (void)htole16(i++); if (i != 3) return 7;
  return 0;
}
static int fork_once(int complete)
{
  pid_t child = fork();
  int status;
  if (child < 0) return 1;
  if (!child) {
    int old = initialized;
    alarm(15);
    if (pthread_once(&once,initialize) || initialized != old + !complete) _exit(2);
    if (pthread_mutex_lock(&lock) || pthread_mutex_unlock(&lock)) _exit(3);
    if (!pthread_self()) _exit(4);
    _exit(0);
  }
  if (wait(&status)!=child || !WIFEXITED(status) || WEXITSTATUS(status)) return 5;
  return 0;
}
int main(void)
{
  cthread_t threads[4];
  pthread_mutex_t dynamic;
  pthread_mutexattr_t unsupported = {0};
  int i;
  alarm(45);
  if (byte_order()) return 1;
  main_thread = pthread_self();
  if (!main_thread || !pthread_equal(main_thread,pthread_self())) return 2;
  if (pthread_mutex_init(&dynamic,&unsupported)!=EINVAL || pthread_mutex_init(&dynamic,0)) return 3;
  if (pthread_mutex_lock(&dynamic) || pthread_mutex_trylock(&dynamic)!=EBUSY || pthread_mutex_destroy(&dynamic)!=EBUSY) return 4;
  if (pthread_mutex_unlock(&dynamic) || pthread_mutex_trylock(&dynamic) || pthread_mutex_unlock(&dynamic) || pthread_mutex_destroy(&dynamic)) return 5;
  if (pthread_once(0,initialize)!=EINVAL || pthread_once(&once,0)!=EINVAL) return 6;
  if (fork_once(0) || initialized) return 7;
  for (i=0;i<4;++i) if (!(threads[i]=cthread_fork(worker,0))) return 8;
  for (i=0;i<4;++i) if (cthread_join(threads[i])) return 9;
  if (count!=8000 || initialized!=1) return 10;
  if (fork_once(1) || initialized!=1) return 11;
  if (condition_tests()) return 12;
  if (pthread_mutex_destroy(&lock)) return 13;
  puts("PASS threading subset: 4 workers, 8000 increments, once publication, identity, mutex errors, 400 condition handshakes, fork and byte order");
  return 0;
}
