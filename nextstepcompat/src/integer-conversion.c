/* ISO C integer conversion for the ILP32 NEXTSTEP C library.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <limits.h>
#include <ctype.h>
#include <errno.h>
#include <unistd.h>

struct conversion {
  unsigned long long value;
  int negative, overflow;
};
static unsigned digit(unsigned char c)
{
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'z') return c - 'a' + 10;
  if (c >= 'A' && c <= 'Z') return c - 'A' + 10;
  return 255;
}
static struct conversion convert(const char *text, char **end, int base,
                                unsigned long long positive_limit,
                                unsigned long long negative_limit)
{
  const char *s = text, *first;
  struct conversion result = {0, 0, 0};
  unsigned long long limit, cutoff;
  unsigned remainder, d;
  if (end) *end = (char *)text;
  if (base && (base < 2 || base > 36)) { errno = EINVAL; return result; }
  while (isspace((unsigned char)*s)) ++s;
  if (*s == '-' || *s == '+') { result.negative = *s == '-'; ++s; }
  if ((!base || base == 16) && s[0] == '0' && (s[1] == 'x' || s[1] == 'X')
      && digit((unsigned char)s[2]) < 16) { s += 2; base = 16; }
  if (!base) base = *s == '0' ? 8 : 10;
  limit = result.negative ? negative_limit : positive_limit;
  cutoff = limit / (unsigned)base;
  remainder = limit % (unsigned)base;
  first = s;
  while ((d = digit((unsigned char)*s)) < (unsigned)base) {
    if (!result.overflow) {
      if (result.value > cutoff || (result.value == cutoff && d > remainder))
        result.overflow = 1;
      else result.value = result.value * (unsigned)base + d;
    }
    ++s;
  }
  if (s != first && end) *end = (char *)s;
  if (result.overflow) { errno = ERANGE; result.value = limit; }
  return result;
}
/* Retain the native symbols for existing binaries. Header aliases select
   these adapters only for applications built with NextStepCompat. */
long ns33_strtol(const char *text, char **end, int base)
{
  const unsigned long long limit = LONG_MAX;
  struct conversion c = convert(text, end, base, limit, limit + 1);
  if (!c.negative) return (long)c.value;
  if (c.value == limit + 1) return LONG_MIN;
  return -(long)c.value;
}
unsigned long ns33_strtoul(const char *text, char **end, int base)
{
  const unsigned long long limit = ULONG_MAX;
  struct conversion c = convert(text, end, base, limit, limit);
  return c.negative && !c.overflow ? 0UL - (unsigned long)c.value : (unsigned long)c.value;
}
long long strtoll(const char *text, char **end, int base)
{
  const unsigned long long limit = __LONG_LONG_MAX__;
  struct conversion c = convert(text, end, base, limit, limit + 1);
  if (!c.negative) return (long long)c.value;
  if (c.value == limit + 1) return -__LONG_LONG_MAX__ - 1;
  return -(long long)c.value;
}
unsigned long long strtoull(const char *text, char **end, int base)
{
  const unsigned long long limit = ~0ULL;
  struct conversion c = convert(text, end, base, limit, limit);
  return c.negative && !c.overflow ? 0ULL - c.value : c.value;
}
long long atoll(const char *text) { return strtoll(text, 0, 10); }
long long llabs(long long value) { return value < 0 ? -value : value; }
lldiv_t lldiv(long long numerator, long long denominator)
{
  lldiv_t value;
  value.quot = numerator / denominator;
  value.rem = numerator % denominator;
  return value;
}
void _Exit(int status) { _exit(status); }
