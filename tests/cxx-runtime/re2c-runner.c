/* Execute the actual upstream generator and compare complete output files.
   Fixture data is generated from the pinned release by prepare-re2c-cases.py.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include "re2c-cases.h"

static int run(const char *tool, const struct re2c_case *test)
{
  int status;
  int child = fork();
  if (child == 0) {
    if (!test)
      execl(tool, tool, "--version", (char *)0);
    else if (test->conditions)
      execl(tool, tool, "--no-generation-date", "--no-version", "-i", "-c",
            "input.re", "-o", "output.c", (char *)0);
    else
      execl(tool, tool, "--no-generation-date", "--no-version", "-i",
            "input.re", "-o", "output.c", (char *)0);
    _exit(127);
  }
  if (child < 0 || wait(&status) != child)
    return 1;
  return !WIFEXITED(status) || WEXITSTATUS(status) != 0;
}

int main(int argc, char **argv)
{
  char tool[1024], scratch[1024];
  char *slash;
  unsigned i;
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
  strcpy(slash + 1, "re2c");
  if (argc > 1 && strlen(argv[1]) + 12 < sizeof(scratch))
    sprintf(scratch, "%s/re2c-cases", argv[1]);
  else
    strcpy(scratch, "/private/tmp/re2c-cases");
  if (mkdir(scratch, 0700) || chdir(scratch)) { perror(scratch); return 2; }
  failures += run(tool, 0);
  for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
    const struct re2c_case *test = &cases[i];
    FILE *f = fopen("input.re", "wb");
    unsigned offset = 0;
    int bad = 0, c;
    if (!f) return 2;
    if (fwrite(test->input, 1, test->input_size, f) != test->input_size) return 2;
    if (fclose(f)) return 2;
    bad = run(tool, test);
    if (!bad) {
      f = fopen("output.c", "rb");
      if (!f) return 2;
      while ((c = fgetc(f)) != EOF) {
        if (offset >= test->expected_size || c != test->expected[offset]) bad = 1;
        ++offset;
      }
      bad |= ferror(f) || offset != test->expected_size;
      fclose(f);
    }
    printf("re2c case %s: %s\n", test->name, bad ? "FAIL" : "PASS");
    failures += bad;
    unlink("input.re"); unlink("output.c");
  }
  chdir(".."); rmdir("re2c-cases");
  printf("re2c application: %u generation cases, %d failures\n", i, failures);
  return failures != 0;
}
