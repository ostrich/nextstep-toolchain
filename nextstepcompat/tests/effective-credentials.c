/* Native effective-ID declarations and reversible child-only privilege tests.
   SPDX-License-Identifier: 0BSD */
#include <unistd.h>
#include <sys/wait.h>
#include <errno.h>
#include <stdio.h>
static int child_test(void)
{
  uid_t uid = geteuid();
  gid_t gid = getegid();
  if (uid != 0 || gid != 0) return 77;
  if (seteuid(uid) || setegid(gid)) return 1;
  if (setegid((gid_t)65534) || getegid() != (gid_t)65534) return 2;
  if (seteuid((uid_t)65534) || geteuid() != (uid_t)65534) return 3;
  errno = 0;
  if (seteuid((uid_t)1) != -1 || errno != EPERM || geteuid() != (uid_t)65534) return 4;
  errno = 0;
  if (setegid((gid_t)1) != -1 || errno != EPERM || getegid() != (gid_t)65534) return 5;
  if (seteuid(uid) || geteuid() != uid || getuid() != 0) return 6;
  if (setegid(gid) || getegid() != gid || getgid() != 0) return 7;
  return 0;
}
int main(void)
{
  int status;
  pid_t child;
  alarm(20);
  child = fork();
  if (child < 0) return 1;
  if (!child) _exit(child_test());
  if (wait(&status) != child || !WIFEXITED(status) || WEXITSTATUS(status)) {
    printf("effective credentials child status %d\n", status);
    return 2;
  }
  if (geteuid() != 0 || getegid() != 0) return 3;
  puts("PASS effective credentials: native no-op, child drop, denied changes, restore; parent unchanged");
  return 0;
}
