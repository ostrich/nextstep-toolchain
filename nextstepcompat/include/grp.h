/* Native BSD account enumeration, hidden in the POSIX namespace.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_GRP_H
#define NEXTSTEPCOMPAT_GRP_H
#include_next <grp.h>
#ifdef __cplusplus
extern "C" {
#endif
struct group *getgrent(void);
void setgrent(void);
void endgrent(void);
int setgroups(int, const gid_t *) __asm__("_ns33_setgroups");
int initgroups(const char *, int);
#ifdef __cplusplus
}
#endif
#endif
