/* Native BSD declarations in modern headers, with libc.h compatibility.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <sys/wait.h>
/* Isolate the SDK's unrelated legacy wait3/readlink prototypes. This test
   checks coexistence of the four newly exposed declarations, not libc.h as
   a whole against modern POSIX interfaces. */
#ifndef __cplusplus
#define wait3 test_native_wait3
#define readlink test_native_readlink
#include <libc.h>
#undef wait3
#undef readlink
#endif
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
static int (*mode_function)(int, int) = fchmod;
static int (*owner_function)(int, int, int) = fchown;
static int (*node_function)(const char *, int, int) = mknod;
static int (*root_function)(const char *) = chroot;
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "filesystem declaration line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  char file[96], linkname[96], fifo[96], target[96];
  int fd, link_created = 0, fifo_created = 0;
  struct stat st;
  snprintf(file, sizeof file, "/tmp/ns33-declarations-%d.file", getpid());
  snprintf(linkname, sizeof linkname, "/tmp/ns33-declarations-%d.link", getpid());
  snprintf(fifo, sizeof fifo, "/tmp/ns33-declarations-%d.fifo", getpid());
  fd = open(file, O_CREAT | O_EXCL | O_RDWR, 0600);
  CHECK(fd >= 0);
  if (fd < 0) return 1;
  errno = 0; CHECK(root_function(file) == -1 && errno == ENOTDIR);
  CHECK(mode_function(fd, 0640) == 0);
  CHECK(fstat(fd, &st) == 0 && (st.st_mode & 0777) == 0640);
  CHECK(owner_function(fd, -1, -1) == 0);
  errno = 0; CHECK(mode_function(-1, 0600) == -1 && errno == EBADF);
  errno = 0; CHECK(owner_function(-1, -1, -1) == -1 && errno == EBADF);
  link_created = symlink(file, linkname) == 0;
  CHECK(link_created);
  if (link_created) {
    CHECK(lstat(linkname, &st) == 0 && S_ISLNK(st.st_mode));
    memset(target, 0, sizeof target);
    CHECK(readlink(linkname, target, sizeof target - 1) == (ssize_t)strlen(file));
    CHECK(!strcmp(target, file));
    CHECK(unlink(linkname) == 0);
  }
  fifo_created = node_function(fifo, S_IFIFO | 0600, 0) == 0;
  CHECK(fifo_created);
  if (fifo_created) {
    CHECK(lstat(fifo, &st) == 0 && S_ISFIFO(st.st_mode));
    CHECK(unlink(fifo) == 0);
  }
  CHECK(close(fd) == 0);
  CHECK(unlink(file) == 0);
  printf("filesystem declarations: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
