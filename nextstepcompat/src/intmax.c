/* C99 maximum-width integer operations. SPDX-License-Identifier: 0BSD */
#include <inttypes.h>
#include <stdlib.h>
_Static_assert(sizeof(intmax_t) == sizeof(long long), "intmax ABI");
_Static_assert(sizeof(uintmax_t) == sizeof(unsigned long long), "uintmax ABI");
intmax_t strtoimax(const char *text, char **end, int base)
{
  return strtoll(text, end, base);
}
uintmax_t strtoumax(const char *text, char **end, int base)
{
  return strtoull(text, end, base);
}
intmax_t imaxabs(intmax_t value) { return value < 0 ? -value : value; }
imaxdiv_t imaxdiv(intmax_t numerator, intmax_t denominator)
{
  imaxdiv_t value;
  value.quot = numerator / denominator;
  value.rem = numerator % denominator;
  return value;
}
