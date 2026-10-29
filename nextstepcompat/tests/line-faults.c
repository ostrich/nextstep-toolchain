/* Fault injection into the exact line-input implementation, without
   interposing the guest allocator globally. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <errno.h>
#include <unistd.h>
static int reject_allocation;
static void *injected_realloc(void *p, size_t size)
{
  if (reject_allocation) { errno = ENOMEM; return 0; }
  return realloc(p, size);
}
#define realloc injected_realloc
#define getdelim tested_getdelim
#define getline tested_getline
#include "../src/getdelim.c"
#undef realloc
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "line-input fault line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  FILE *f = tmpfile();
  char *line = 0, *saved;
  size_t capacity = 0;
  int fd;
  if (!f) return 2;
  CHECK(fputs("abcdef\n", f) >= 0);
  CHECK(fflush(f) == 0 && fseek(f, 0, SEEK_SET) == 0);
  reject_allocation = 1;
  errno = 0;
  CHECK(getline(&line, &capacity, f) == -1 && errno == ENOMEM && ferror(f));
  CHECK(!line && capacity == 0 && ftell(f) == 0);
  clearerr(f);
  line = malloc(3); if (!line) return 2;
  strcpy(line, "xx"); saved = line; capacity = 3;
  errno = 0;
  CHECK(getline(&line, &capacity, f) == -1 && errno == ENOMEM && ferror(f));
  CHECK(line == saved && capacity == 3 && !strcmp(line, "ab") && ftell(f) == 2);
  clearerr(f); reject_allocation = 0;
  CHECK(getline(&line, &capacity, f) == 5 && !strcmp(line, "cdef\n"));
  errno = 0;
  CHECK(getline(0, &capacity, f) == -1 && errno == EINVAL);
  clearerr(f);
  errno = 0;
  CHECK(getline(&line, 0, f) == -1 && errno == EINVAL);
  CHECK(fclose(f) == 0);
  f = tmpfile(); if (!f) return 2;
  fd = fileno(f); CHECK(close(fd) == 0);
  errno = 0;
  CHECK(getline(&line, &capacity, f) == -1 && ferror(f) && errno == EBADF);
  fclose(f); free(line);
  printf("line-input faults: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
