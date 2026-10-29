/* Differential check against the host libc, including extended precision.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include <float.h>

extern float nextstep_strtof(const char *, char **);
extern double nextstep_strtod(const char *, char **);
extern long double nextstep_strtold(const char *, char **);
static unsigned checks, failures;

#define TEST(type, suffix) do { \
  char *a, *b; int ea, eb; \
  errno = 73; type x = strto##suffix(text, &a); ea = errno; \
  errno = 73; type y = nextstep_strto##suffix(text, &b); eb = errno; \
  ++checks; \
  if (!((isnan(x) && isnan(y)) || (x == y && !!signbit(x) == !!signbit(y))) \
      || a != b || (ea != eb && !(a == text && eb == EINVAL) && !(fpclassify(x) == FP_SUBNORMAL && eb == ERANGE && ea == 73))) { \
    if (failures++ < 30) printf("%s %s: %La/%La end %ld/%ld errno %d/%d\n", \
      #suffix, text, (long double)x, (long double)y, (long)(a-text), (long)(b-text), ea, eb); \
  } \
} while (0)

static void check(const char *text)
{
  TEST(float, f); TEST(double, d); TEST(long double, ld);
}

int main(void)
{
  static const char *const edge[] = {"", " ", "+", "-", ".", "1.25tail", "  -0tail",
    "0x", "0x.", "0x.1p", "0x1p-", "0x1.8p+1", "inf", "-INFINITYtail",
    "infinite", "nan", "-nan", "NAN()", "nan(payload)", "nan(unclosed", "nan(a-b)",
    "1e", "1e+", "1e-2tail", "1e99999999", "-1e-99999999",
    "2.2250738585072014e-308", "4.9406564584124654e-324",
    "1.00000000000000011102230246251565404236316680908203125",
    "1.0000000000000000000542101086242752217003726400434970855712890625"};
  unsigned i, state = 1739;
  char text[256];
  for (i = 0; i < sizeof(edge)/sizeof(edge[0]); ++i) check(edge[i]);
  for (i = 0; i < 5000; ++i) {
    state = state * 1664525u + 1013904223u;
    sprintf(text, "%s%u.%09ue%dend", state & 1 ? "-" : "", state,
            state ^ 0x12345678u, (int)((state >> 8) % 10001) - 5000);
    check(text);
    sprintf(text, "%s0x%x.%08xp%dend", state & 1 ? "-" : "", state,
            state ^ 0x12345678u, (int)((state >> 8) % 34001) - 17000);
    check(text);
  }
  {
    char *huge = malloc(40032);
    if (!huge) return 2;
    memset(huge, '7', 40000); strcpy(huge + 40000, "e-39999end"); check(huge);
    huge[0] = '0'; huge[1] = '.'; memset(huge + 2, '0', 39998);
    strcpy(huge + 40000, "1e40000end"); check(huge);
    free(huge);
  }
  printf("floating parse host differential: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
