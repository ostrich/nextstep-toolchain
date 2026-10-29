/* Native pointer interoperability and safe huge-request failures.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
extern void *original_malloc(size_t) __asm__("_malloc");
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "native allocation line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  size_t i;
  unsigned char *p, *q;
  volatile size_t huge = 0x40000000UL;
  errno = 0; CHECK(malloc(huge) == 0 && errno == ENOMEM);
  errno = 0; CHECK(calloc(huge, 4) == 0 && errno == ENOMEM);
  errno = 0; CHECK(calloc((size_t)-1, 2) == 0 && errno == ENOMEM);
  p = calloc(32, 16);
  CHECK(p != 0);
  if (!p) return 1;
  for (i = 0; i < 512; ++i) CHECK(p[i] == 0);
  memset(p, 0x5a, 512);
  errno = 0;
  CHECK(realloc(p, huge) == 0 && errno == ENOMEM);
  for (i = 0; i < 512; ++i) CHECK(p[i] == 0x5a);
  q = realloc(p, 8192);
  CHECK(q != 0);
  if (!q) { free(p); return 1; }
  for (i = 0; i < 512; ++i) CHECK(q[i] == 0x5a);
  CHECK(realloc(q, 32) == q);
  free(q);
  p = original_malloc(257);
  CHECK(p != 0);
  if (!p) return 1;
  memset(p, 0x73, 257);
  q = realloc(p, 16384);
  CHECK(q != 0);
  if (!q) { free(p); return 1; }
  for (i = 0; i < 257; ++i) CHECK(q[i] == 0x73);
  free(q);
  p = malloc(0); free(p);
  p = calloc(0, (size_t)-1); free(p);
  p = realloc(0, 0); free(p);
  p = malloc(16);
  CHECK(p != 0);
  if (!p) return 1;
  q = realloc(p, 0);
  if (q) free(q); else free(p);
  printf("native allocation: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
