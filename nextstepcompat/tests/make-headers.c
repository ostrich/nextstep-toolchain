/* Include-order and native ABI regression checks exposed by pristine Make. */
#include <stddef.h>
struct dirent;
struct directory_hooks { struct dirent *(*read)(void *); };
#include <dirent.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <alloca.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#if defined(__STRICT_ANSI__) && !__STRICT_ANSI__
#error Invalid SDK feature macro
#endif
_Static_assert(sizeof(struct dirent) == sizeof(struct direct), "directory size");
_Static_assert(offsetof(struct dirent, d_name) == offsetof(struct direct, d_name), "directory name");
_Static_assert(offsetof(struct dirent, d_namlen) == offsetof(struct direct, d_namlen), "directory length");
_Static_assert(sizeof(union wait) == sizeof(int), "wait status word");
static struct dirent *read_entry(void *p) { return readdir(p); }
int main(void)
{
  struct directory_hooks hooks = {read_entry};
  char *stack = alloca(32), temp[] = "/tmp/ns33-make-XXXXXX";
  DIR *d = opendir("/"); struct dirent *entry; int found = 0, fd, pid, status, got;
  if (!d) return 1;
  while ((entry = hooks.read(d))) {
    if (strlen(entry->d_name) != entry->d_namlen) return 2;
    ++found;
  }
  if (closedir(d) || !found) return 3;
  strcpy(stack, "stack works"); if (strcmp(stack, "stack works")) return 4;
  fd = mkstemp(temp); if (fd < 0) return 5;
  if (write(fd, "123456", 6) != 6 || ftruncate(fd, 2) || lseek(fd, 0, SEEK_END) != 2) return 6;
  if (close(fd) || unlink(temp)) return 7;
  pid = fork(); if (!pid) _exit(37); if (pid < 0) return 8;
  do { got = wait3(&status, 0, 0); } while (got < 0 && errno == EINTR);
  if (got != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 37) return 9;
  pid = vfork(); if (!pid) _exit(23); if (pid < 0) return 10;
  do { got = wait3(&status, 0, 0); } while (got < 0 && errno == EINTR);
  if (got != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 23) return 11;
  {
    static char buffer[] = "NS33_PUTENV=one";
    char *owned;
    if (putenv(buffer) || strcmp(getenv("NS33_PUTENV"), "one")) return 12;
    strcpy(strchr(buffer, '=') + 1, "two");
    if (strcmp(getenv("NS33_PUTENV"), "two")) return 13;
    if (setenv("NS33_PUTENV", "copy", 1) || strcmp(getenv("NS33_PUTENV"), "copy")) return 14;
    if (putenv(buffer) || unsetenv("NS33_PUTENV") || getenv("NS33_PUTENV")) return 15;
    if (setenv("NS33_PUTENV", "owned", 1)) return 16;
    owned = getenv("NS33_PUTENV") - strlen("NS33_PUTENV=");
    if (putenv(owned) || strcmp(getenv("NS33_PUTENV"), "owned")) return 17;
    if (unsetenv("NS33_PUTENV")) return 18;
    errno = 0; if (putenv("=bad") != -1 || errno != EINVAL) return 19;
  }
  puts("MAKE HEADER ABI PASS"); return 0;
}
