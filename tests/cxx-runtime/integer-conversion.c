/* SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include "integer-vectors.h"
extern char *getwd(char *);
#ifdef __NeXT__
extern int symlink(const char *, const char *);
#endif
static int expected_errno(int kind) { return kind == 1 ? ERANGE : kind == 2 ? EINVAL : 73; }
int main(int argc, char **argv)
{
  unsigned i, failures = 0, checks = 0;
  char *end, *allocated, resolved[1024] = "";
  const char *path = argc > 2 ? argv[2] : "/mach_kernel";
  const char *volatile minimum = "-9223372036854775808";
#define CHECK(value, label) do { ++checks; if (!(value)) { ++failures; printf("FAIL %s\n", label); } } while (0)
  for (i = 0; i < sizeof(integer_vectors) / sizeof(integer_vectors[0]); ++i) {
    const struct integer_vector *v = &integer_vectors[i];
    unsigned long long bits;
    errno = 73; end = (char *)v->text;
    bits = (unsigned long long)strtoll(v->text, &end, v->base); ++checks;
    if (bits != v->signed_bits || end - v->text != v->signed_end || errno != expected_errno(v->signed_errno)) {
      if (failures++ < 5) printf("FAIL signed vector %u base %d\n", i, v->base);
    }
    errno = 73; end = (char *)v->text;
    bits = strtoull(v->text, &end, v->base); ++checks;
    if (bits != v->unsigned_bits || end - v->text != v->unsigned_end || errno != expected_errno(v->unsigned_errno)) {
      if (failures++ < 5) printf("FAIL unsigned vector %u base %d\n", i, v->base);
    }
  }
  CHECK(atoll(minimum) == -__LONG_LONG_MAX__ - 1, "atoll minimum");
  CHECK(realpath(path, resolved) && resolved[0] == '/', "realpath caller buffer");
  allocated = realpath(path, 0); ++checks;
  if (!allocated || strcmp(allocated, resolved)) ++failures;
  free(allocated);
  errno = 0; allocated = realpath("/no-such-numeric-test-input", 0); ++checks;
  if (allocated || errno != ENOENT) ++failures;
  free(allocated);
  {
    char native_cwd[1024] = "", small[1];
    char root[512], child[512], file[512], alias[512], cycle[512], candidate[512];
    char *cwd, *after;
    FILE *stream;
    getwd(native_cwd);
    cwd = getcwd(0, 0);
    CHECK(cwd && native_cwd[0] == '/' && !strcmp(cwd, native_cwd), "getcwd matches native reference");
    errno = 0;
    CHECK(!getcwd(small, sizeof(small)) && errno == ERANGE, "getcwd buffer bounds");
    snprintf(root, sizeof(root), "%s/integer-path-test", argc > 1 ? argv[1] : "/private/tmp");
    if (mkdir(root, 0700)) { perror("path fixture directory"); free(cwd); return 1; }
    snprintf(child, sizeof(child), "%s/child", root);
    snprintf(file, sizeof(file), "%s/file", child);
    snprintf(alias, sizeof(alias), "%s/alias", root);
    snprintf(cycle, sizeof(cycle), "%s/cycle", root);
    CHECK(!mkdir(child, 0700), "mkdir path child");
    stream = fopen(file, "w");
    CHECK(stream != 0, "create path file");
    if (stream) fclose(stream);
    CHECK(!symlink("child", alias), "create relative symlink");
    snprintf(candidate, sizeof(candidate), "%s/../child/file", alias);
    allocated = realpath(candidate, 0);
    CHECK(allocated && !strcmp(allocated, file), "resolve symlink before parent component");
    free(allocated);
    snprintf(candidate, sizeof(candidate), "%s/..", file);
    errno = 0; allocated = realpath(candidate, 0);
    CHECK(!allocated && errno == ENOTDIR, "file cannot be traversed as directory");
    free(allocated);
    CHECK(!symlink("cycle", cycle), "create symlink loop");
    errno = 0; allocated = realpath(cycle, 0);
    CHECK(!allocated && errno == ELOOP, "bounded symlink loop");
    free(allocated);
    CHECK(!chdir(root), "enter nested path fixture");
    allocated = getcwd(0, 0);
    CHECK(allocated && !strcmp(allocated, root), "getcwd across nested and mounted directories");
    free(allocated);
    allocated = realpath("alias/../child/file", 0);
    CHECK(allocated && !strcmp(allocated, file), "relative realpath from nested directory");
    free(allocated);
    CHECK(!chdir(native_cwd), "restore fixture cwd");
    after = getcwd(0, 0);
    CHECK(cwd && after && !strcmp(cwd, after), "path resolution preserves cwd");
    free(cwd); free(after);
    unlink(cycle); unlink(alias); unlink(file); rmdir(child); rmdir(root);
  }
  printf("integer conversion: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
