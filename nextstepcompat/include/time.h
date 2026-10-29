/* POSIX time representation missing from the original C89 SDK.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_TIME_H
#define NEXTSTEPCOMPAT_TIME_H
#include_next <time.h>
#ifndef CLOCKS_PER_SEC
/* The native ANSI time.h specifies clock() ticks through this C89 name. */
#define CLOCKS_PER_SEC CLK_TCK
#endif
#ifdef __cplusplus
extern "C" {
#endif
struct tm *localtime_r(const time_t *, struct tm *) __asm__("_ns33_localtime_r");
struct tm *gmtime_r(const time_t *, struct tm *) __asm__("_ns33_gmtime_r");
size_t strftime(char *, size_t, const char *, const struct tm *) __asm__("_ns33_strftime");
#ifdef __cplusplus
}
#endif
/* Realtime uses native gettimeofday; monotonic is explicitly unsupported. */
#ifndef CLOCK_REALTIME
#define CLOCK_REALTIME 0
#endif
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
#endif
typedef int clockid_t;
struct timespec {
  time_t tv_sec;
  long tv_nsec;
};
#ifdef __cplusplus
extern "C" {
#endif
int clock_gettime(clockid_t, struct timespec *) __asm__("_ns33_clock_gettime");
#ifdef __cplusplus
}
#endif
#endif
