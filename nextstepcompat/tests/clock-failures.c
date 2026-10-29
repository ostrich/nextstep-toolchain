/* Error propagation without writing a partial result.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
#include <sys/time.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
static unsigned calls;
static int clock_test_gettimeofday(struct timeval *result, void *zone)
{
  (void)result; (void)zone;
  calls++;
  errno = EIO;
  return -1;
}
#define gettimeofday clock_test_gettimeofday
#include "../src/clock-realtime.c"
#undef gettimeofday
int main(void)
{
  struct timespec result = {123, 456};
  assert(ns33_clock_gettime(CLOCK_REALTIME, &result) == -1);
  assert(errno == EIO && calls == 1);
  assert(result.tv_sec == 123 && result.tv_nsec == 456);
  assert(ns33_clock_gettime(CLOCK_MONOTONIC, &result) == -1);
  assert(errno == ENOTSUP && calls == 1);
  assert(ns33_clock_gettime(999, &result) == -1);
  assert(errno == EINVAL && calls == 1);
  assert(result.tv_sec == 123 && result.tv_nsec == 456);
  puts("PASS realtime clock failure propagation");
  return 0;
}
