/* Boundary tests with controlled native calls. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
static int page = 4096, fail;
static unsigned calls, frees;
static size_t requested;
static unsigned char storage[128], old_storage[128];
static void *allocate(size_t size)
{
  ++calls; requested = size;
  return fail ? 0 : storage;
}
static size_t allocated_size(void *p) { return 64; }
static void release(void *p) { if (p == old_storage) ++frees; }
static int pagesize(void) { return page; }
#define NS33_NATIVE_MALLOC allocate
#define NS33_NATIVE_SIZE allocated_size
#define NS33_NATIVE_FREE release
#define NS33_NATIVE_PAGESIZE pagesize
#include "../src/native-allocator.c"
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "allocator guard line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  int p;
  size_t size;
  unsigned before;
  for (p = 512; p <= 65536; p *= 2) {
    page = p;
    size = 0x3fffffffUL - 39 - (p - 1);
    before = calls;
    CHECK(ns33_malloc(size) == storage && requested == size);
    errno = 0;
    CHECK(!ns33_malloc(size + 1) && errno == ENOMEM);
    CHECK(calls == before + 1);
    /* Model the documented worst-case native rounding/region overhead. */
    CHECK((((size + 4 + 7) & ~(size_t)7) + 20 + p - 1) /
          p * p + 8 <= 0x3fffffffUL);
  }
  page = 4096;
  before = calls;
  errno = 0; CHECK(!ns33_malloc(0x40000000UL) && errno == ENOMEM);
  errno = 0; CHECK(!ns33_malloc((size_t)-1) && errno == ENOMEM);
  errno = 0; CHECK(!ns33_calloc((size_t)-1, 2) && errno == ENOMEM);
  CHECK(calls == before);
  memset(storage, 0xa5, sizeof storage);
  CHECK(ns33_calloc(8, 16) == storage);
  for (size = 0; size < sizeof storage; ++size) CHECK(!storage[size]);
  CHECK(ns33_calloc(0, (size_t)-1) == storage && requested == 0);
  CHECK(ns33_calloc((size_t)-1, 0) == storage && requested == 0);
  memset(old_storage, 0x6b, sizeof old_storage);
  before = frees;
  errno = 0;
  CHECK(!ns33_realloc(old_storage, 0x40000000UL) && errno == ENOMEM);
  CHECK(frees == before && old_storage[0] == 0x6b);
  fail = 1;
  errno = 0; CHECK(!ns33_malloc(32) && errno == ENOMEM);
  errno = 0; CHECK(!ns33_calloc(4, 8) && errno == ENOMEM);
  errno = 0; CHECK(!ns33_realloc(old_storage, 128) && errno == ENOMEM);
  CHECK(frees == before && old_storage[127] == 0x6b);
  fail = 0;
  CHECK(ns33_realloc(old_storage, 32) == old_storage && frees == before);
  CHECK(ns33_realloc(old_storage, 128) == storage);
  CHECK(frees == before + 1 && !memcmp(storage, old_storage, 64));
  CHECK(ns33_realloc(0, 16) == storage && frees == before + 1);
  CHECK(ns33_realloc(old_storage, 0) == storage && frees == before + 2);
  page = 0;
  before = calls;
  errno = 0; CHECK(!ns33_malloc(32) && errno == ENOMEM && calls == before);
  page = -1;
  CHECK(!ns33_malloc(0) && calls == before);
  printf("allocator guards: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
