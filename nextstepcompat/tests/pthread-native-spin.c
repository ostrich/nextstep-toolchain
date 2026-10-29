/* A bounded child isolates a suspected native SPARC spin_lock defect.
   SPDX-License-Identifier: 0BSD */
#include <mach/cthreads.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#include <string.h>
static struct mutex spin = MUTEX_INITIALIZER;
static struct mutex ready_lock = MUTEX_INITIALIZER;
static struct condition ready_cond = CONDITION_INITIALIZER;
static int started;
static void *worker(void *unused)
{
  (void)unused;
  mutex_lock(&ready_lock); started = 1; condition_signal(&ready_cond); mutex_unlock(&ready_lock);
  spin_lock(&spin.lock);
  spin_unlock(&spin.lock);
  return 0;
}
int main(void)
{
  pid_t child = fork();
  int status;
  if (child < 0) return 1;
  if (!child) {
    cthread_t t;
    port_t port;
    msg_header_t message;
    alarm(10); cthread_init();
    if (!mutex_try_lock(&spin)) _exit(2);
    t = cthread_fork(worker, 0);
    mutex_lock(&ready_lock);
    while (!started) condition_wait(&ready_cond, &ready_lock);
    mutex_unlock(&ready_lock);
    if (port_allocate(task_self(), &port) != KERN_SUCCESS) _exit(5);
    memset(&message, 0, sizeof(message));
    message.msg_size = sizeof(message); message.msg_local_port = port;
    if (msg_receive(&message, RCV_TIMEOUT, 50) != RCV_TIMED_OUT) _exit(6);
    port_deallocate(task_self(), port);
    spin_unlock(&spin.lock);
    cthread_join(t); _exit(0);
  }
  if (wait(&status) != child) return 2;
  if (WIFSIGNALED(status) && WTERMSIG(status) == SIGALRM)
    puts("PASS native spin_lock characterization: contended child hit bounded alarm");
  else if (WIFEXITED(status) && WEXITSTATUS(status) == 0)
    puts("PASS native spin_lock characterization: contended child completed");
  else {
    printf("FAIL native spin_lock child status=%x\n", status); return 3;
  }
  return 0;
}
