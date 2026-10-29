/* Run staged binaries after the test report filesystem has mounted.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/wait.h>

int main(int argc, char **argv)
{
  static const char *const names[] = {"abi", "stdlib", "threads", "atomics",
    "objects-only", "c-smoke", "objcxx", "floating-conversion",
    "floating-immediates", "numeric-cxx", "c99-cxx", "flatc-runner", "re2c-runner"};
  unsigned i, failures = 0;
  if (argc != 4 || chdir(argv[1])) return 2;
  for (i = 0; i < sizeof(names)/sizeof(names[0]); ++i) {
    char path[1024]; int child, got, status;
    if (snprintf(path, sizeof(path), "%s/%s", argv[1], names[i]) >= sizeof(path)) return 2;
    printf("BATCH RUN %s\n", names[i]); fflush(stdout);
    child = fork();
    if (!child) { execl(path, path, argv[2], argv[3], (char *)0); _exit(127); }
    if (child < 0) return 2;
    do { got = wait(&status); } while ((got < 0 && errno == EINTR) || (got > 0 && got != child));
    if (got != child) return 2;
    printf("BATCH EXIT %s %d\n", names[i], WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    failures += !WIFEXITED(status) || WEXITSTATUS(status) != 0;
    fflush(stdout);
  }
  printf("runtime batch: %u programs, %u failures\n", i, failures);
  return failures != 0;
}
