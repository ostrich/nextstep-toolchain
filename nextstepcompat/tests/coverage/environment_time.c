/* Deterministic environment ownership and civil-time coverage.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <locale.h>
#include <errno.h>
extern char **environ;
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "environment/time line %d: %s\n", __LINE__, #x); } } while (0)
static void environment(void)
{
  unsigned i;
  char name[] = "NS33_COVERAGE", value[] = "original";
  char **saved = environ;
  char a[] = "NS33_COVERAGE=first", b[] = "OTHER=keep", c[] = "NS33_COVERAGE=duplicate";
  char *alternate[] = {a, b, c, 0};
  environ = alternate;
  CHECK(unsetenv(name) == 0 && !getenv(name));
  CHECK(environ[0] == b && environ[1] == 0);
  CHECK(setenv(name, value, 0) == 0);
  value[0] = 'X'; CHECK(getenv(name) && !strcmp(getenv(name), "original"));
  CHECK(setenv(name, "ignored", 0) == 0 && !strcmp(getenv(name), "original"));
  for (i = 0; i < 1000; ++i) {
    CHECK(setenv(name, i & 1 ? "odd" : "even", 1) == 0);
    CHECK(getenv(name) && !strcmp(getenv(name), i & 1 ? "odd" : "even"));
  }
  CHECK(setenv(name, "", 1) == 0 && getenv(name) && !*getenv(name));
  CHECK(unsetenv(name) == 0 && !getenv(name));
  CHECK(unsetenv(name) == 0);
  errno = 0; CHECK(setenv("", "x", 1) == -1 && errno == EINVAL);
  errno = 0; CHECK(setenv("a=b", "x", 1) == -1 && errno == EINVAL);
  errno = 0; CHECK(unsetenv("") == -1 && errno == EINVAL);
  errno = 0; CHECK(unsetenv("a=b") == -1 && errno == EINVAL);
  environ = 0;
  CHECK(setenv(name, "empty-vector", 1) == 0 && !strcmp(getenv(name), "empty-vector"));
  CHECK(unsetenv(name) == 0 && !getenv(name));
  {
    char buffer[] = "NS33_PUTENV_CHECK=one";
    CHECK(putenv(buffer) == 0);
    CHECK(!strcmp(getenv("NS33_PUTENV_CHECK"), "one"));
    strcpy(strchr(buffer, '=') + 1, "two");
    CHECK(!strcmp(getenv("NS33_PUTENV_CHECK"), "two"));
    CHECK(setenv("NS33_PUTENV_CHECK", "copy", 1) == 0);
    CHECK(putenv(buffer) == 0);
    CHECK(!strcmp(getenv("NS33_PUTENV_CHECK"), "two"));
    CHECK(putenv("NS33_PUTENV_CHECK") == 0 && !getenv("NS33_PUTENV_CHECK"));
    errno = 0; CHECK(putenv("=bad") == -1 && errno == EINVAL);
  }
  environ = saved;
}
static void civil_time(void)
{
  time_t epoch = 0, later = 86400;
  struct tm t, *p;
  char text[128];
  CHECK(setlocale(LC_TIME, "C") != 0);
  CHECK(setenv("TZ", "UTC0", 1) == 0);
  tzset();
  p = gmtime(&epoch); CHECK(p != 0); if (!p) return;
  t = *p;
  CHECK(t.tm_year == 70 && t.tm_mon == 0 && t.tm_mday == 1 && t.tm_hour == 0);
  CHECK(t.tm_wday == 4 && t.tm_yday == 0);
  CHECK(difftime(later, epoch) == 86400.0);
  CHECK(strftime(text, sizeof text, "%Y-%m-%d %H:%M:%S", &t) == 19);
  CHECK(!strcmp(text, "1970-01-01 00:00:00"));
  CHECK(strftime(text, sizeof text, "%a %A %b %B %j %w %U %W %%", &t) > 0);
  if (strcmp(text, "Thu Thursday Jan January 001 4 00 00 %")) fprintf(stderr, "C90 time actual=[%s]\n", text);
  CHECK(!strcmp(text, "Thu Thursday Jan January 001 4 00 00 %"));
  CHECK(strftime(text, 2, "%Y", &t) == 0);
  text[0] = 'x'; CHECK(strftime(text, 0, "%Y", &t) == 0 && text[0] == 'x');
  CHECK(mktime(&t) == epoch);
  t.tm_mon = 1; t.tm_mday = 29; t.tm_year = 100;
  epoch = mktime(&t); CHECK(epoch != (time_t)-1);
  p = gmtime(&epoch); CHECK(p && p->tm_year == 100 && p->tm_mon == 1 && p->tm_mday == 29);
  CHECK(strftime(text, sizeof text, "%F %T %C %u %V %G %g", &t) > 0);
  if (strcmp(text, "2000-02-29 00:00:00 20 2 09 2000 00")) fprintf(stderr, "C99 time actual=[%s]\n", text);
  CHECK(!strcmp(text, "2000-02-29 00:00:00 20 2 09 2000 00"));
}
int main(void)
{
  environment(); civil_time();
  printf("environment/time: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
