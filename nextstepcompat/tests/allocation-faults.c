/* Exercise imported allocation helpers with NeXT-style malloc failures.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
static int reject_allocation;
static void *injected_malloc(size_t size)
{
  if (reject_allocation) return 0;
  return malloc(size);
}
#define malloc injected_malloc
#include "../src/allocator-bridge.c"
#undef malloc
#define malloc ns33_compat_malloc
#define strdup tested_strdup
#define strndup tested_strndup
#define vasprintf tested_vasprintf
#include "../string/strdup.c"
#include "../string/strndup.c"
#include "../format/allocation/vasprintf.c"
#undef malloc
static int allocating_format(char **text, const char *format, ...)
{
  int result;
  va_list ap;
  va_start(ap, format);
  result = tested_vasprintf(text, format, ap);
  va_end(ap);
  return result;
}
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "allocation fault line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  char *text = 0;
  reject_allocation = 1;
  errno = 0; CHECK(tested_strdup("abc") == 0 && errno == ENOMEM);
  errno = 0; CHECK(tested_strndup("abc", 2) == 0 && errno == ENOMEM);
  errno = 0; CHECK(allocating_format(&text, "%s:%d", "abc", 17) == -1 && errno == ENOMEM);
  reject_allocation = 0;
  text = tested_strdup("abc"); CHECK(text && !strcmp(text, "abc")); free(text);
  text = tested_strndup("abc", 2); CHECK(text && !strcmp(text, "ab")); free(text);
  CHECK(allocating_format(&text, "%s:%d", "abc", 17) == 6);
  CHECK(text && !strcmp(text, "abc:17")); free(text);
  printf("allocation faults: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
