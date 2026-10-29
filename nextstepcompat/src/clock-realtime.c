/* POSIX realtime timestamps over the native microsecond wall clock.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
#include <sys/time.h>
#include <errno.h>

int ns33_clock_gettime(clockid_t clock, struct timespec *result)
{
  struct timeval now;
  if (clock != CLOCK_REALTIME) {
    errno = clock == CLOCK_MONOTONIC ? ENOTSUP : EINVAL;
    return -1;
  }
  if (gettimeofday(&now, 0)) return -1;
  result->tv_sec = now.tv_sec;
  result->tv_nsec = now.tv_usec * 1000L;
  return 0;
}
