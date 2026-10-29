/* Compare complete upstream flatc outputs with independently generated oracles.
   Keep scratch files on failure for diagnosis. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include "flatc-cases.h"

static int execute(const char *tool, const char *const *args)
{
  int status, child = fork(), got;
  if (!child) { execv(tool, (char *const *)args); _exit(127); }
  if (child < 0) { perror("fork"); return 1; }
  do { got = wait(&status); } while ((got < 0 && errno == EINTR) || (got > 0 && got != child));
  if (got != child) { perror("wait"); return 1; }
  if (!WIFEXITED(status) || WEXITSTATUS(status)) {
    printf("flatc child status: %d\n", status); return 1;
  }
  return 0;
}

static int compare(const struct flatc_file *expected)
{
  FILE *f = fopen(expected->name, "rb");
  unsigned offset = 0;
  int c, bad = 0;
  if (!f) { perror(expected->name); return 1; }
  while ((c = fgetc(f)) != EOF) {
    if (!bad && (offset >= expected->size || c != expected->data[offset])) {
      printf("%s: first mismatch at byte %u (actual %d, expected %d)\n",
             expected->name, offset, c,
             offset < expected->size ? expected->data[offset] : -1);
      bad = 1;
    }
    ++offset;
  }
  if (ferror(f) || offset != expected->size) {
    printf("%s: actual size %u, expected %u\n", expected->name, offset,
           expected->size); bad = 1;
  }
  if (fclose(f)) bad = 1;
  return bad;
}

int main(int argc, char **argv)
{
  static const char *const dirs[] = {"include", "include/sub", "cpp", "schema", "binary", "json"};
  char tool[1024], scratch[1024], *slash;
  unsigned i, j;
  int failures = 0;
  if (argv[0][0] == '/') {
    if (strlen(argv[0]) >= sizeof(tool)) return 2;
    strcpy(tool, argv[0]);
  } else {
    if (!getcwd(tool, sizeof(tool))) return 2;
    if (strlen(tool) + strlen(argv[0]) + 2 > sizeof(tool)) return 2;
    strcat(tool, "/"); strcat(tool, argv[0]);
  }
  slash = strrchr(tool, '/');
  if (!slash || (unsigned)(slash - tool) + 7 > sizeof(tool)) return 2;
  strcpy(slash + 1, "flatc");
  if (snprintf(scratch, sizeof(scratch), "%s/flatc-cases",
               argc > 1 ? argv[1] : "/private/tmp") >= sizeof(scratch)) return 2;
  if (mkdir(scratch, 0700) || chdir(scratch)) { perror(scratch); return 2; }
  for (i = 0; i < sizeof(dirs) / sizeof(dirs[0]); ++i)
    if (mkdir(dirs[i], 0700)) { perror(dirs[i]); return 2; }
  for (i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i) {
    FILE *f = fopen(inputs[i].name, "wb");
    if (!f) { perror(inputs[i].name); return 2; }
    if (fwrite(inputs[i].data, 1, inputs[i].size, f) != inputs[i].size) return 2;
    if (fclose(f)) return 2;
  }
  for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
    int bad;
    printf("flatc case %s: starting\n", cases[i].name); fflush(stdout);
    bad = execute(tool, cases[i].arguments);
    if (!bad)
      for (j = 0; j < cases[i].count; ++j) bad |= compare(&cases[i].outputs[j]);
    printf("flatc case %s: %s\n", cases[i].name, bad ? "FAIL" : "PASS");
    fflush(stdout); failures += bad;
  }
  printf("flatc application: %u generation cases, %d failures\n", i, failures);
  return failures != 0;
}
