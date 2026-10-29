/* SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/stat.h>
/* The SDK hides this BSD declaration in the POSIX feature profile. */
extern int mknod(const char *, int, int);
int mkfifo(const char *path, mode_t mode)
{
  return mknod(path, S_IFIFO | (mode & 07777), 0);
}
