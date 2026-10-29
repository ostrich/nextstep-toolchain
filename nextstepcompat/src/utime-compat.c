/* Native utime dereferences a NULL time buffer. The kernel also rejects
   utimes(NULL), so construct the current times explicitly. Native ownership
   restrictions still apply, including on non-owner writable files.
   SPDX-License-Identifier: 0BSD */
#include <sys/time.h>
#include <utime.h>
#include <errno.h>
extern int ns33_native_utime(const char *, const struct utimbuf *) __asm__("_utime");

int ns33_utime(const char *path, const struct utimbuf *times)
{
  struct timeval now;
  struct utimbuf current;
  if (!path) { errno = EFAULT; return -1; }
  if (!*path) { errno = ENOENT; return -1; }
  if (!times) {
    if (gettimeofday(&now, 0)) return -1;
    current.actime = current.modtime = now.tv_sec;
    times = &current;
  }
  return ns33_native_utime(path, times);
}
