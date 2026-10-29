/* General string and C99 math interfaces absent from NEXTSTEP libc.
   strcasestr follows musl 1.2.6 (MIT, see options/COPYRIGHT).
   Remaining adapters: SPDX-License-Identifier: 0BSD */
#include <string.h>
#include <strings.h>
#include <signal.h>
#include <math.h>
#include <limits.h>
#include <errno.h>
extern const char *ns33_native_siglist[] __asm__("_sys_siglist");
char *ns33_strsignal(int number)
{
  return number > 0 && number < NSIG ? (char *)ns33_native_siglist[number] : "Unknown signal";
}
char *ns33_stpcpy(char *destination, const char *source)
{
  while ((*destination = *source)) { ++destination; ++source; }
  return destination;
}
char *ns33_strcasestr(const char *haystack, const char *needle)
{
  size_t length = strlen(needle);
  if (!length) return (char *)haystack;
  for (; *haystack; ++haystack)
    if (!strncasecmp(haystack, needle, length)) return (char *)haystack;
  return 0;
}
long ns33_lround(double value)
{
  double rounded = round(value);
  if (!isfinite(rounded) || rounded > (double)LONG_MAX || rounded < (double)LONG_MIN) {
    errno = EDOM;
    return LONG_MIN;
  }
  return (long)rounded;
}
