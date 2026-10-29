/* Safe current-time handling over the original timestamp API.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_UTIME_H
#define NEXTSTEPCOMPAT_UTIME_H
#include_next <utime.h>
#ifdef __cplusplus
extern "C" {
#endif
int utime(const char *, const struct utimbuf *) __asm__("_ns33_utime");
#ifdef __cplusplus
}
#endif
#endif
