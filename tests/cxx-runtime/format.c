/* SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <string.h>
#include <float.h>
#include <limits.h>

static int failures;
static void print_value(const char *name, const char *format, long double value)
{
  char buffer[512];
  int count = snprintf(buffer, sizeof(buffer), format, value);
  printf("%s|%d|%s\n", name, count, buffer);
}
int main(void)
{
  char buffer[128], short_buffer[4];
  int count;
  print_value("third", "%.21Lg", 1.0L / 3.0L);
  print_value("fixed", "%+.24Lf", 1.0L / 3.0L);
  print_value("small", "%.21Le", LDBL_MIN);
  print_value("large", "%.21Le", LDBL_MAX);
  print_value("negative-zero", "%+.4Lf", -0.0L);
  print_value("hex", "%La", 1.5L);
  print_value("integer", "%.0Lf", 0x1p63L + 1.0L);
  print_value("round-even", "%.0Lf", 2.5L);
  print_value("round-odd", "%.0Lf", 3.5L);
  count = snprintf(buffer, sizeof(buffer), "%lld:%llu:%#llx",
                   -9223372036854775807LL - 1,
                   18446744073709551615ULL, 0x123456789abcdef0ULL);
  printf("integers|%d|%s\n", count, buffer);
  count = snprintf(buffer, sizeof(buffer), "%2$d:%1$d", 12, 34);
  printf("positional|%d|%s\n", count, buffer);
  memset(short_buffer, 1, sizeof(short_buffer));
  count = snprintf(short_buffer, sizeof(short_buffer), "%s", "abcdef");
  if (count != 6 || strcmp(short_buffer, "abc")) ++failures;
  if (snprintf(0, 0, "%s:%d", "abcdef", 123) != 10) ++failures;
  count = snprintf(buffer, sizeof(buffer), "%08d %.3s", -42, "abcdef");
  printf("fields|%d|%s\n", count, buffer);
  /* Deterministic exponent and precision coverage, compared with the host
     libc oracle. The Intel host and target both use IEEE extended precision. */
  {
    unsigned long long state = 0x6a09e667f3bcc909ULL;
    int i;
    for (i = 0; i != 200; ++i) {
      int exponent, rest;
      long double value;
      state ^= state << 13; state ^= state >> 7; state ^= state << 17;
      value = (long double)state / 0x1p64L;
      exponent = (int)(state % 32001) - 16000;
      rest = exponent;
      while (rest >= 32) { value *= 0x1p32L; rest -= 32; }
      while (rest <= -32) { value *= 0x1p-32L; rest += 32; }
      while (rest > 0) { value *= 2.0L; --rest; }
      while (rest < 0) { value *= 0.5L; ++rest; }
      if (i & 1) value = -value;
      count = snprintf(buffer, sizeof(buffer), "%.*Le", i % 37, value);
      printf("corpus-%d|%d|%s\n", i, count, buffer);
    }
  }
  printf("format: %d failures\n", failures);
  return failures != 0;
}
