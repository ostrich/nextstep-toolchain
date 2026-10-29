/* Publish the native select entry point with its existing timeval ABI.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_TIME_H
#define NEXTSTEPCOMPAT_SYS_TIME_H
#include <sys/types.h>
#include_next <sys/time.h>
#ifdef __cplusplus
extern "C" {
#endif
int select(int, fd_set *, fd_set *, fd_set *, struct timeval *);
#ifdef __cplusplus
}
#endif
#endif
