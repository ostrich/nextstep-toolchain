/* Native BSD filesystem query declarations omitted by sys/vfs.h.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_VFS_H
#define NEXTSTEPCOMPAT_SYS_VFS_H
#include <sys/types.h>
#include_next <sys/vfs.h>
#ifdef __cplusplus
extern "C" {
#endif
int statfs(const char *, struct statfs *);
int fstatfs(int, struct statfs *);
#ifdef __cplusplus
}
#endif
#endif
