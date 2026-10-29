/* Public POSIX accessor over the original directory-stream ABI.
   SPDX-License-Identifier: 0BSD */
#include <dirent.h>
#include <unistd.h>
#include <errno.h>
int dirfd(DIR *directory)
{
  return directory->dd_fd;
}

/* The original remove is unlink-only and rejects directories with EPERM. */
int ns33_remove(const char *path)
{
  int saved;
  if (unlink(path) == 0) return 0;
  saved = errno;
  if (saved != EPERM && saved != EISDIR) return -1;
  if (rmdir(path) == 0) return 0;
  if (errno == ENOTDIR) errno = saved;
  return -1;
}
