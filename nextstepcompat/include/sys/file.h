/* BSD file locking over the original native interface.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_FILE_H
#define NEXTSTEPCOMPAT_SYS_FILE_H
#include_next <sys/file.h>
#ifdef __cplusplus
extern "C" {
#endif
int flock(int, int);
#ifdef __cplusplus
}
#endif
#endif
