/* Gregorian dates spanning a full 400-year cycle, without mktime/time_t.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
#include <stdio.h>
#include <string.h>
#include <locale.h>
struct vector { int year, month, day, yday, wday; const char *c90, *c99; };
#include "time-vectors.h"
int main(void)
{
  unsigned i, failures = 0;
  char text[128];
  struct tm t;
  if (!setlocale(LC_TIME, "C")) return 2;
  for (i = 0; i < sizeof vectors / sizeof *vectors; ++i) {
    const struct vector *v = vectors + i;
    memset(&t, 0, sizeof t);
    t.tm_year = v->year; t.tm_mon = v->month; t.tm_mday = v->day;
    t.tm_yday = v->yday; t.tm_wday = v->wday;
    if (strftime(text, sizeof text, "%Y %m %d %j %w %U %W", &t) != strlen(v->c90) || strcmp(text, v->c90)) {
      if (failures++ < 5) fprintf(stderr, "C90 calendar expected=[%s] actual=[%s]\n", v->c90, text);
    }
    if (strftime(text, sizeof text, "%F %C %u %V %G %g", &t) != strlen(v->c99) || strcmp(text, v->c99)) {
      if (failures++ < 5) fprintf(stderr, "C99 calendar expected=[%s] actual=[%s]\n", v->c99, text);
    }
  }
  printf("calendar: %u checks, %u failures\n", (unsigned)(2 * sizeof vectors / sizeof *vectors), failures);
  return failures != 0;
}
