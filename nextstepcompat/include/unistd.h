/* Request the original SDK's POSIX declarations.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_UNISTD_H
#define NEXTSTEPCOMPAT_UNISTD_H
#ifndef _POSIX_SOURCE
#define _POSIX_SOURCE 1
#endif
#include_next <unistd.h>
#ifdef __cplusplus
extern "C" {
#endif
ssize_t readlink(const char *, char *, size_t);
int ftruncate(int, off_t);
int truncate(const char *, off_t);
int fsync(int);
int gethostname(char *, int);
int sethostname(const char *, int);
int killpg(int, int);
char *crypt(const char *, const char *);
int usleep(unsigned int);
int getpagesize(void);
int getdtablesize(void);
int gethostid(void);
/* Match the native libc.h declarations, which unistd.h omits. */
#include <getopt.h>
int setpgrp(int, int);
int setpgid(pid_t, pid_t);
int fchown(int, int, int);
int symlink(const char *, const char *);
int chroot(const char *);
int seteuid(uid_t);
int setegid(gid_t);
char *getpass(char *);
void sync(void);
int nice(int);
int setreuid(int, int);
int setregid(int, int);
pid_t vfork(void);
pid_t fork(void) __asm__("_ns33_fork");
pid_t getpgrp(void) __asm__("_ns33_getpgrp");
int getgroups(int, gid_t *) __asm__("_ns33_getgroups");
#ifdef __cplusplus
}
#endif
#endif
