/* POSIX FIFO constructor missing from the native library.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_STAT_H
#define NEXTSTEPCOMPAT_SYS_STAT_H
#include <sys/types.h>
#include_next <sys/stat.h>
#ifndef S_ISLNK
#define S_ISLNK(mode) (((mode) & _S_IFMT) == _S_IFLNK)
#endif
#ifndef S_ISSOCK
#define S_ISSOCK(mode) (((mode) & _S_IFMT) == _S_IFSOCK)
#endif
#ifdef __cplusplus
extern "C" {
#endif
int mkfifo(const char *, mode_t);
/* Preserve the native libc.h signatures, including promoted mode/device
   arguments, while exposing these functions in their modern headers. */
int fchmod(int, int);
int mknod(const char *, int, int);
#ifdef __cplusplus
}
#endif
#endif
