/* Target execution checks independent of the native parser.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <errno.h>

extern float strtof(const char *, char **);
extern long double strtold(const char *, char **);

static unsigned checks, failures;
#define CHECK(value) do { ++checks; if (!(value)) { ++failures; printf("FAIL line %u\n", __LINE__); } } while (0)

int main(void)
{
  static const struct {
    const char *input;
    long double value;
    unsigned end;
  } cases[] = {
    {"1.25tail", 1.25L, 4}, {"  -1.25rest", -1.25L, 7},
    {"0x1.8p+1tail", 3.0L, 8}, {"-0x1.8p-1tail", -0.75L, 9},
    {"1e+tail", 1.0L, 1}, {"0x.tail", 0.0L, 1},
    {"17.125e2tail", 1712.5L, 8}, {"0.0009765625", 0x1p-10L, 12},
    {"9007199254740991tail", 9007199254740991.0L, 16}
  };
  unsigned i;
  char *end;
  long double value;
  for (i = 0; i < sizeof(cases)/sizeof(cases[0]); ++i) {
    const char *s = cases[i].input;
    float f = strtof(s, &end);
    CHECK(f == (float)cases[i].value); CHECK(end == s + cases[i].end);
    double d = strtod(s, &end);
    CHECK(d == (double)cases[i].value); CHECK(end == s + cases[i].end);
    value = strtold(s, &end);
    CHECK(value == cases[i].value); CHECK(end == s + cases[i].end);
  }
  CHECK(isnan(strtod("nan(payload)", &end)) && !*end);
  CHECK(isinf(strtod("-INFINITY", &end)) && !*end);
  CHECK(signbit(strtod("-0", &end)) && !*end);
  CHECK(isnan(strtold("nan", &end)) && !*end);
  CHECK(isinf(strtold("inf", &end)) && !*end);
  CHECK(signbit(strtold("-0", &end)) && !*end);
  errno = 73; value = strtold("1e99999", &end);
  CHECK(isinf(value) && errno == ERANGE && !*end);
  errno = 73; value = strtold("-1e-99999", &end);
  CHECK(value == 0 && signbit(value) && errno == ERANGE && !*end);
  errno = 73; CHECK(isinf(strtof("0x1p128", &end)) && errno == ERANGE);
  errno = 73; CHECK(isinf(strtod("0x1p1024", &end)) && errno == ERANGE);
  CHECK(strtod("1.00000000000000011102230246251565404236316680908203125", &end) == 1.0);
  CHECK(strtod("1.00000000000000011102230246251565404236316680908203126", &end) == 0x1.0000000000001p0);
#if LDBL_MANT_DIG == 64
  CHECK(strtold("1.000000000000000000108420217248550443400745280086994171142578125", &end) == 0x1.0000000000000002p0L);
#else
  CHECK(strtold("1.00000000000000011102230246251565404236316680908203126", &end) == 0x1.0000000000001p0L);
#endif
  printf("floating conversion: %u checks, %u failures; long double %u bits\n", checks, failures, LDBL_MANT_DIG);
  return failures != 0;
}
