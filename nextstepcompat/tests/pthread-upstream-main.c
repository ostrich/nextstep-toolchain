/* Entry point and bounded timing helpers for selected Open POSIX tests.
   This is test scaffolding, not a new system nanosleep implementation.
   SPDX-License-Identifier: 0BSD */
#include <mach/cthreads.h>
#include <time.h>
#include <sys/time.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>
extern int test_main(int, char **);
int ns33_test_nanosleep(const struct timespec *time, struct timespec *remaining)
{
  port_t port;
  msg_header_t message;
  struct timeval now;
  long long end, delta;
  unsigned ms;
  int status;
  if (!time || time->tv_sec < 0 || time->tv_nsec < 0 || time->tv_nsec >= 1000000000L) {
    errno = EINVAL; return -1;
  }
  if (port_allocate(task_self(), &port) != KERN_SUCCESS) { errno = ENOMEM; return -1; }
  gettimeofday(&now, 0);
  end = (long long)now.tv_sec*1000000 + now.tv_usec +
        (long long)time->tv_sec*1000000 + (time->tv_nsec+999)/1000;
  for (;;) {
    gettimeofday(&now, 0);
    delta = end - ((long long)now.tv_sec*1000000 + now.tv_usec);
    if (delta <= 0) break;
    ms = delta > 1000000 ? 1000 : (unsigned)((delta+999)/1000);
    memset(&message, 0, sizeof(message));
    message.msg_size = sizeof(message); message.msg_local_port = port;
    status = msg_receive(&message, RCV_TIMEOUT, ms);
    if (status != RCV_TIMED_OUT && status != RCV_INTERRUPTED) {
      port_deallocate(task_self(), port); errno = EIO; return -1;
    }
  }
  port_deallocate(task_self(), port);
  if (remaining) remaining->tv_sec = remaining->tv_nsec = 0;
  return 0;
}
unsigned ns33_test_sleep(unsigned seconds)
{ struct timespec t = {seconds,0}; return ns33_test_nanosleep(&t, 0) ? seconds : 0; }
int main(int argc, char **argv)
{
  alarm(45);
  return test_main(argc, argv);
}
