/* Initial-thread exit must be joinable and must not become process status.
   SPDX-License-Identifier: 0BSD */
#include <pthread.h>
#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>
static pthread_t initial;
static void *join_initial(void *unused)
{
  void *result;
  (void)unused;
  if (pthread_join(initial, &result) || result != (void *)123) _exit(3);
  return 0;
}
int main(void)
{
  pid_t child = fork();
  int status;
  if (child < 0) return 1;
  if (!child) {
    pthread_t worker;
    alarm(20); initial = pthread_self();
    if (pthread_create(&worker, 0, join_initial, 0)) _exit(2);
    pthread_exit((void *)123);
  }
  if (wait(&status) != child || !WIFEXITED(status) || WEXITSTATUS(status)) return 4;
  puts("PASS initial-thread pthread_exit, join value and zero final process status");
  return 0;
}
