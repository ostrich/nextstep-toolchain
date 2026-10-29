/* Native facts, deliberately independent of the pthread adapter.
   SPDX-License-Identifier: 0BSD */
#include <mach/cthreads.h>
#include <mach/message.h>
#include <mach/thread_info.h>
#include <mach/mach_host.h>
#include <sys/time.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "native FAIL %d: %s\n", __LINE__, #x); exit(2); } } while (0)
static struct mutex lock = MUTEX_INITIALIZER;
static struct condition cond = CONDITION_INITIALIZER;
static int ready, release_worker, thread_error, global_error;
static void *worker(void *unused)
{
  sigset_t set;
  thread_sched_info_data_t info;
  unsigned count = THREAD_SCHED_INFO_COUNT;
  thread_t kernel = thread_self();
  kern_return_t status;
  (void)unused;
  status = thread_info(kernel, THREAD_SCHED_INFO, (thread_info_t)&info, &count);
  printf("NATIVE scheduling query=%d policy=%d priority=%d worker-port-match=%d\n",
         status, status == KERN_SUCCESS ? info.policy : -1,
         status == KERN_SUCCESS ? info.base_priority : -1,
         cthread_thread(cthread_self()) == kernel);
  if (status == KERN_SUCCESS) {
    kern_return_t fixed = thread_policy(kernel, POLICY_FIXEDPRI, 10);
    printf("NATIVE fixed-priority policy request=%d\n", fixed);
    if (fixed == KERN_SUCCESS)
      CHECK(thread_policy(kernel, info.policy, info.data) == KERN_SUCCESS);
    CHECK(thread_priority(kernel, info.base_priority, FALSE) == KERN_SUCCESS);
  }
  /* Mach 2 caches this borrowed name. Do not apply Mach 3 send-right
     reference-counting rules to thread_self(). */
  CHECK(cthread_self() && cthread_self()->func);
  CHECK(sigemptyset(&set) == 0 && sigaddset(&set, SIGUSR1) == 0);
  CHECK(sigprocmask(SIG_BLOCK, &set, 0) == 0);
  CHECK(open("/no-such-pthread-probe-dir/file", O_RDONLY) == -1);
  thread_error = cthread_errno(); global_error = errno;
  mutex_lock(&lock); ready = 1; condition_signal(&cond);
  while (!release_worker) condition_wait(&cond, &lock);
  mutex_unlock(&lock);
  return (void *)17;
}
int main(void)
{
  port_t port;
  cthread_t t;
  msg_header_t m;
  struct timeval begin, end;
  sigset_t original, observed;
  alarm(30); cthread_init();
  CHECK(cthread_self() && !cthread_self()->func);
  CHECK(sigprocmask(SIG_BLOCK, 0, &original) == 0);
  t = cthread_fork(worker, 0); CHECK(t != 0);
  mutex_lock(&lock);
  while (!ready) condition_wait(&cond, &lock);
  CHECK(sigprocmask(SIG_BLOCK, 0, &observed) == 0);
  CHECK(sigismember(&observed, SIGUSR1) == 1);
  release_worker = 1; condition_signal(&cond); mutex_unlock(&lock);
  CHECK(cthread_join(t) == (void *)17);
  CHECK(sigprocmask(SIG_SETMASK, &original, 0) == 0);
  printf("NATIVE process-wide mask confirmed; per-cproc errno=%d global errno=%d\n", thread_error, global_error);
  CHECK(thread_error == ENOENT);
  CHECK(port_allocate(task_self(), &port) == KERN_SUCCESS);
  m = (msg_header_t){0}; m.msg_simple = 1; m.msg_size = sizeof(m); m.msg_remote_port = port;
  CHECK(msg_send(&m, SEND_TIMEOUT, 0) == SEND_SUCCESS);
  m = (msg_header_t){0}; m.msg_size = sizeof(m); m.msg_local_port = port;
  CHECK(msg_receive(&m, RCV_TIMEOUT, 0) == RCV_SUCCESS);
  CHECK(gettimeofday(&begin, 0) == 0);
  m = (msg_header_t){0}; m.msg_size = sizeof(m); m.msg_local_port = port;
  CHECK(msg_receive(&m, RCV_TIMEOUT, 20) == RCV_TIMED_OUT);
  CHECK(gettimeofday(&end, 0) == 0);
  CHECK(((long long)end.tv_sec - begin.tv_sec)*1000000 + end.tv_usec - begin.tv_usec >= 19000);
  CHECK(port_deallocate(task_self(), port) == KERN_SUCCESS);
  printf("PASS native pthread prerequisites: queued Mach wake, timed receive, Cthread lifecycle; stack mask=%x\n", (unsigned)cthread_stack_mask);
  return 0;
}
