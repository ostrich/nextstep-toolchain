/* Reduced valid-input failures and regression boundaries.
   Build without NS33_EXTENDED as the native-library negative control.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <stdarg.h>
#ifdef NS33_EXTENDED
#include <wchar.h>
#endif
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "regression %u line %d: %s\n", checks, __LINE__, #x); } } while (0)

static void integers(void)
{
  const char *s;
  char *end;
  CHECK(strstr("", "") != 0);
  s = "abc";
  CHECK(strstr(s, "") == s);
  CHECK(strstr(s, "bc") == s + 1);
  CHECK(strstr(s, "d") == 0);
  s = "0xz";
  CHECK(strtol(s, &end, 16) == 0 && end == s + 1);
  s = "-0Xz";
  CHECK(strtol(s, &end, 0) == 0 && end == s + 2);
  s = "-1!";
  CHECK(strtoul(s, &end, 10) == ULONG_MAX && end == s + 2);
  s = "184467440737095516160!";
  errno = 0;
  CHECK(strtoul(s, &end, 10) == ULONG_MAX && errno == ERANGE && *end == '!');
  s = "999999999999999999999!";
  errno = 0;
  CHECK(strtol(s, &end, 10) == LONG_MAX && errno == ERANGE && *end == '!');
  s = "-999999999999999999999!";
  errno = 0;
  CHECK(strtol(s, &end, 10) == LONG_MIN && errno == ERANGE && *end == '!');
  s = " +z";
  CHECK(strtol(s, &end, 10) == 0 && end == s);
  errno = 0;
  CHECK(strtol("23", &end, 36) == 75 && errno == 0);
}

static void scanning(void)
{
  int a = -1, b = -1, n = -1;
  double d = -1;
  char text[16] = {0}, tail = 0;
  CHECK(sscanf("011 0x100", "%i %i%n", &a, &b, &n) == 2);
  CHECK(a == 9 && b == 256 && n == 9);
  CHECK(sscanf("0x1234p56", "%lf", &d) == 1 && d == 0x1234p56);
  CHECK(sscanf("10e", "%lf", &d) == 0);
  CHECK(sscanf("abcdef", "%3[a-z]%c%n", text, &tail, &n) == 2);
  CHECK(!strcmp(text, "abc") && tail == 'd' && n == 4);
#ifdef NS33_EXTENDED
  {
    signed char tiny = 0;
    short small = 0;
    long long big = 0;
    long double extended = 0;
    wchar_t wide[8] = {0};
    CHECK(sscanf("-12 123 -9223372036854775808 1.25", "%hhd %hd %lld %Lf",
                 &tiny, &small, &big, &extended) == 4);
    CHECK(tiny == -12 && small == 123 && big == LLONG_MIN && extended == 1.25L);
    CHECK(sscanf("word", "%ls", wide) == 1 && wide[0] == 'w' && wide[4] == 0);
    CHECK(sscanf("34 12", "%2$d %1$d", &a, &b) == 2 && a == 12 && b == 34);
    CHECK(sscanf("123X", "%*2d%d%c", &a, &tail) == 2 && a == 3 && tail == 'X');
  }
#endif
}

static void streams(void)
{
  FILE *f = tmpfile();
  char text[32] = {0};
  int i = -1;
  CHECK(f != 0);
  if (!f) return;
  CHECK(fprintf(f, "%s:%d", "abc", 12) == 6);
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  CHECK(fscanf(f, "%[z]", text) == 0);
  CHECK(ungetc('x', f) == 'x');
  CHECK(fgetc(f) == 'x');
  CHECK(fgetc(f) == 'a');
  CHECK(fseek(f, 0, SEEK_SET) == 0);
  CHECK(fscanf(f, "%3[a-z]:%d", text, &i) == 2);
  CHECK(!strcmp(text, "abc") && i == 12);
  CHECK(fgetc(f) == EOF && feof(f));
#ifdef __NeXT__
  printf("EOF pushback precondition: count=%d flags=%x\n", f->_cnt, (unsigned)f->_flag);
#endif
  CHECK(ungetc(0x1ff, f) == 255);
  CHECK(!feof(f));
  CHECK(fgetc(f) == 255);
#ifdef NS33_EXTENDED
  for (i = 0; i < 256; ++i) {
    CHECK(fgetc(f) == EOF);
    CHECK(fgetc(f) == EOF);
    CHECK(ungetc(i, f) == i);
    CHECK(!feof(f));
    CHECK(fgetc(f) == i);
  }
#endif
  CHECK(fclose(f) == 0);
  f = fopen("/dev/null", "r");
  CHECK(f != 0);
  if (f) {
    CHECK(fprintf(f, "abc") < 0 && ferror(f));
    CHECK(fclose(f) == 0);
  }
#ifdef NS33_EXTENDED
  {
    struct { unsigned char before; char data[2]; unsigned char after; } buffer = {19, {0}, 71};
    f = tmpfile(); CHECK(f != 0);
    if (!f) return;
    CHECK(setvbuf(f, buffer.data, _IOFBF, 2) == 0);
    CHECK(fwrite("ab", 1, 2, f) == 2 && fseek(f, 0, SEEK_SET) == 0);
    CHECK(fscanf(f, "%[z]", text) == 0);
    CHECK(ungetc('x', f) == 'x');
    CHECK(fgetc(f) == 'x' && fgetc(f) == 'a' && fgetc(f) == 'b');
    CHECK(fclose(f) == 0 && buffer.before == 19 && buffer.after == 71);
#ifdef __NeXT__
    f = fopen("/dev/null", "w"); CHECK(f != 0);
    if (f) {
      /* A historical error indicator must remain sticky, but does not by
         itself turn a subsequent successful write into a failed write. */
      f->_flag |= _IOERR;
      CHECK(fprintf(f, "%s", "abc") == 3 && ferror(f));
      fclose(f);
    }
#endif
  }
#endif
}
int main(void)
{
  integers(); scanning(); streams();
  printf("libc regressions: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
