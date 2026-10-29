/* Exercise native FILE state through compatibility formatting/scanning.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <errno.h>
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "stdio line %d: %s\n", __LINE__, #x); } } while (0)

#ifdef NS33_COMPAT
static int scan_stdin(const char *format, ...)
{
  va_list ap;
  int result;
  va_start(ap, format);
  result = vscanf(format, ap);
  va_end(ap);
  return result;
}
#endif

static void stream_modes(int buffering)
{
  FILE *f = tmpfile();
  char buffer[32], text[64];
  int i, n;
  CHECK(f != 0);
  if (!f) return;
  CHECK(setvbuf(f, buffer, buffering, sizeof buffer) == 0);
  for (i = 0; i < 40; ++i) {
    n = fprintf(f, "%03d:%s\n", i, "abc");
    CHECK(n == 8);
  }
  CHECK(fflush(f) == 0);
  CHECK(ftell(f) == 320);
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  for (i = 0; i < 40; ++i) {
    int value = -1;
    CHECK(fscanf(f, "%3d:%3[a-z]", &value, text) == 2);
    CHECK(value == i && !strcmp(text, "abc"));
    CHECK(getc(f) == '\n');
  }
  CHECK(getc(f) == EOF && feof(f));
  CHECK(ungetc('Q', f) == 'Q' && !feof(f));
  CHECK(getc(f) == 'Q');
  CHECK(getc(f) == EOF && feof(f));
  CHECK(fwrite("!", 1, 1, f) == 1);
  CHECK(fflush(f) == 0);
  CHECK(ftell(f) == 321);
  CHECK(fseek(f, 0, SEEK_SET) == 0 && !feof(f));
  CHECK(getc(f) == '0');
  CHECK(ungetc('X', f) == 'X');
  CHECK(fseek(f, 8, SEEK_SET) == 0);
  CHECK(getc(f) == '0');
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  CHECK(fprintf(f, "replaced") == 8);
  CHECK(fflush(f) == 0);
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  memset(text, 0, sizeof text);
  n = fread(text, 1, 8, f);
  if (n != 8 || memcmp(text, "replaced", 8))
    fprintf(stderr, "update mode=%d read=%d text=[%s]\n", buffering, n, text);
  CHECK(n == 8 && !memcmp(text, "replaced", 8));
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  CHECK(fwrite("DIRECT", 2, 3, f) == 3);
  CHECK(fflush(f) == 0 && fseek(f, 0, SEEK_SET) == 0);
  CHECK(fread(text, 1, 6, f) == 6 && !memcmp(text, "DIRECT", 6));
  CHECK(fclose(f) == 0);
}

static void stdin_calls(void)
{
  FILE *input = tmpfile();
  int saved, value = -1;
  char text[16];
  CHECK(input != 0);
  if (!input) return;
  CHECK(fputs("011 apple 0x20 pear", input) >= 0);
  CHECK(fflush(input) == 0 && fseek(input, 0, SEEK_SET) == 0);
  saved = dup(0);
  CHECK(saved >= 0);
  if (saved < 0) { fclose(input); return; }
  CHECK(dup2(fileno(input), 0) == 0);
  clearerr(stdin);
  CHECK(scanf("%i %15s", &value, text) == 2);
  CHECK(value == 9 && !strcmp(text, "apple"));
#ifdef NS33_COMPAT
  CHECK(scan_stdin("%i %15s", &value, text) == 2);
  CHECK(value == 32 && !strcmp(text, "pear"));
  CHECK(scan_stdin("%d", &value) == EOF && feof(stdin));
#else
  CHECK(scanf("%i %15s", &value, text) == 2);
#endif
  CHECK(dup2(saved, 0) == 0);
  close(saved);
  clearerr(stdin);
  CHECK(fclose(input) == 0);
}

static void errors(void)
{
  FILE *f = fopen("/dev/null", "r");
  CHECK(f != 0);
  if (f) {
    errno = 0;
    CHECK(fprintf(f, "reject") < 0 && ferror(f));
    clearerr(f);
    CHECK(!ferror(f));
    CHECK(fwrite("reject", 2, 3, f) == 0 && ferror(f));
    clearerr(f);
    CHECK(fwrite("", 0, 1, f) == 0 && !ferror(f));
    CHECK(fclose(f) == 0);
  }
  f = tmpfile();
  CHECK(f != 0);
  if (f) {
    int fd = fileno(f), result;
    CHECK(setvbuf(f, 0, _IONBF, 0) == 0);
    CHECK(close(fd) == 0);
    errno = 0;
    result = fprintf(f, "bad descriptor");
    CHECK(result < 0 && ferror(f) && errno == EBADF);
    /* No descriptor is opened between close and fclose; it cannot close an
       unrelated reused descriptor. The expected close failure is ignored. */
    fclose(f);
  }
}
int main(void)
{
  stream_modes(_IOFBF);
  stream_modes(_IOLBF);
  stream_modes(_IONBF);
  stdin_calls();
  errors();
  printf("stdio boundaries: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
