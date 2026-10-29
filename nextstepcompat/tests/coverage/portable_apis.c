/* Portable additions and allocation/ownership boundaries.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <limits.h>
#include <errno.h>
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "portable line %d: %s\n", __LINE__, #x); } } while (0)

static void strings(void)
{
  char *s, *a, *b, *save1 = 0, *save2 = 0;
  char one[] = ":one::two", two[] = "red,blue", raw[] = {'a', 'b', 'c'};
  size_t i;
  for (i = 0; i <= 6; ++i) CHECK(strnlen("abc", i) == (i < 3 ? i : 3));
  CHECK(strnlen(raw, sizeof raw) == sizeof raw);
  s = strdup("hello"); CHECK(s && !strcmp(s, "hello"));
  if (s) { s[0] = 'H'; CHECK(!strcmp(s, "Hello")); free(s); }
  s = strndup(raw, 2); CHECK(s && !strcmp(s, "ab")); free(s);
  s = strndup(raw, 0); CHECK(s && !*s); free(s);
  s = strndup("x", 100); CHECK(s && !strcmp(s, "x")); free(s);
  a = strtok_r(one, ":", &save1); CHECK(a && !strcmp(a, "one"));
  b = strtok_r(two, ",", &save2); CHECK(b && !strcmp(b, "red"));
  a = strtok_r(0, ":", &save1); CHECK(a && !strcmp(a, "two"));
  b = strtok_r(0, "", &save2); CHECK(b && !strcmp(b, "blue"));
  CHECK(strtok_r(0, ":", &save1) == 0);
  CHECK(strtok_r(0, ",", &save2) == 0);
}

static void lines(void)
{
  FILE *f = tmpfile();
  char *line = 0;
  size_t capacity = 99, i;
  ssize_t n;
  CHECK(f != 0);
  if (!f) return;
  CHECK(fwrite("a\0b\n\n", 1, 5, f) == 5);
  for (i = 0; i < 9000; ++i) CHECK(putc('x', f) == 'x');
  CHECK(fputs("!tail", f) >= 0);
  CHECK(fflush(f) == 0 && fseek(f, 0, SEEK_SET) == 0);
  n = getline(&line, &capacity, f);
  CHECK(n == 4 && capacity >= 5 && !memcmp(line, "a\0b\n\0", 5));
  CHECK(getline(&line, &capacity, f) == 1 && line[0] == '\n' && line[1] == 0);
  n = getdelim(&line, &capacity, '!', f);
  CHECK(n == 9001 && capacity >= 9002 && line[9000] == '!' && !line[9001]);
  for (i = 0; i < 9000; ++i) CHECK(line[i] == 'x');
  CHECK(getline(&line, &capacity, f) == 4 && !strcmp(line, "tail"));
  CHECK(getline(&line, &capacity, f) == -1 && feof(f) && !ferror(f));
  free(line); line = malloc(1); capacity = 1;
  CHECK(line != 0);
  rewind(f);
  CHECK(getdelim(&line, &capacity, 0, f) == 2 && line[0] == 'a' && !line[1] && !line[2]);
  free(line);
  CHECK(fclose(f) == 0);
}

static void integers(void)
{
  char *end, text[128];
  intmax_t value;
  uintmax_t unsigned_value;
  imaxdiv_t d;
  CHECK(strtoimax("-9223372036854775808!", &end, 10) == INTMAX_MIN && *end == '!');
  CHECK(strtoumax("18446744073709551615!", &end, 10) == UINTMAX_MAX && *end == '!');
  errno = 0;
  CHECK(strtoimax("9223372036854775808", &end, 10) == INTMAX_MAX && errno == ERANGE);
  CHECK(imaxabs(-123) == 123);
  d = imaxdiv(-17, 5); CHECK(d.quot == -3 && d.rem == -2);
  CHECK(snprintf(text, sizeof text, "%" PRIdMAX " %" PRIuMAX, INTMAX_MIN, UINTMAX_MAX) == 41);
  CHECK(sscanf(text, "%" SCNdMAX " %" SCNuMAX, &value, &unsigned_value) == 2);
  CHECK(value == INTMAX_MIN && unsigned_value == UINTMAX_MAX);
}

int main(void)
{
  strings(); lines(); integers();
  printf("portable APIs: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
