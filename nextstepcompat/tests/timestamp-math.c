/* Timestamp NULL arguments and floating special values. SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <utime.h>
#include <time.h>
#include <math.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
static int checks, failures;
#define CHECK(condition) do { ++checks; if (!(condition)) { ++failures; \
  printf("FAIL line %d: %s errno=%d\n", __LINE__, #condition, errno); } } while (0)
int main(void)
{
  const char *path = "compat-utime-test";
  FILE *file;
  struct stat status;
  struct utimbuf stamp;
  time_t before, after;
  double result;
  double (*volatile exponential)(double) = exp;
  int child_status;
  pid_t child;
  file = fopen(path, "w");
  CHECK(file != 0);
  if (!file) return 1;
  CHECK(fclose(file) == 0);
  stamp.actime = 500000000; stamp.modtime = 500000123;
  CHECK(utime(path, &stamp) == 0);
  CHECK(stat(path, &status) == 0);
  CHECK(status.st_atime == stamp.actime);
  CHECK(status.st_mtime == stamp.modtime);
  before = time(0);
  CHECK(utime(path, 0) == 0);
  after = time(0);
  CHECK(stat(path, &status) == 0);
  CHECK(status.st_atime >= before && status.st_atime <= after);
  CHECK(status.st_mtime >= before && status.st_mtime <= after);
  errno = 0;
  CHECK(utime("compat-utime-does-not-exist", 0) == -1 && errno == ENOENT);
  errno = 0;
  CHECK(utime("", 0) == -1 && errno == ENOENT);
  errno = 0;
  CHECK(utime(0, 0) == -1 && errno == EFAULT);
  if (geteuid() == 0) {
    CHECK(chmod(path, 0666) == 0);
    child = fork();
    CHECK(child >= 0);
    if (!child) {
      if (setuid(1)) _exit(30);
      _exit(utime(path, 0) == 0 ? 0 : errno == EPERM ? 10 : errno == EACCES ? 11 : 20);
    }
    if (child > 0) {
      CHECK(wait4(child, &child_status, 0, 0) == child);
      CHECK(WIFEXITED(child_status));
      if (WIFEXITED(child_status)) {
        int code = WEXITSTATUS(child_status);
        CHECK(code == 0 || code == 10 || code == 11);
        printf("NOTE non-owner current-time update result=%d (10=EPERM, 11=EACCES)\n", code);
      }
    }
  }
  CHECK(unlink(path) == 0);
  errno = E2BIG;
  result = exponential(INFINITY);
  CHECK(isinf(result) && result > 0);
  CHECK(errno == E2BIG);
  errno = E2BIG;
  result = exponential(-INFINITY);
  CHECK(result == 0.0 && !signbit(result));
  CHECK(errno == E2BIG);
  CHECK(isnan(exponential(NAN)));
  CHECK(exponential(0.0) == 1.0);
  CHECK(fabs(exponential(1.0) - 2.718281828459045) < 1e-12);
  CHECK(fabs(exponential(-1.0) - 0.36787944117144233) < 1e-12);
  printf("TIMESTAMP-MATH %d checks, %d failures\n", checks, failures);
  return failures != 0;
}
