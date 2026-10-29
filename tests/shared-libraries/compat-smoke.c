/* Shared/native environment and representative compatibility APIs. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <regex.h>
extern char **environ;
int main(void)
{
  char buffer[64];
  char *entry = "NS33_SHARED_TEST=putenv";
  char *replacement[] = { "NS33_SHARED_TEST=external", 0 };
  char **saved;
  regex_t expression;
  wchar_t wide;
  if (setenv("NS33_SHARED_TEST", "initial", 1) ||
      !getenv("NS33_SHARED_TEST") || strcmp(getenv("NS33_SHARED_TEST"), "initial")) return 1;
  if (putenv(entry) || strcmp(getenv("NS33_SHARED_TEST"), "putenv")) return 2;
  saved = environ;
  environ = replacement;
  if (setenv("NS33_SHARED_TEST", "replacement", 1) ||
      strcmp(getenv("NS33_SHARED_TEST"), "replacement")) return 3;
  environ = saved;
  if (unsetenv("NS33_SHARED_TEST") || getenv("NS33_SHARED_TEST")) return 4;
  if (snprintf(buffer, sizeof buffer, "%lld:%s", 1234567890123LL, "ok") != 16 ||
      strcmp(buffer, "1234567890123:ok")) return 5;
  if (mbrtowc(&wide, "A", 1, 0) != 1 || wide != L'A') return 6;
  if (regcomp(&expression, "^(alpha|beta)[0-9]+$", REG_EXTENDED)) return 7;
  if (regexec(&expression, "alpha42", 0, 0, 0)) return 8;
  regfree(&expression);
  puts("PASS shared NextStepCompat smoke");
  return 0;
}
