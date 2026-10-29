/* Bit-exact C99 trunc checks, including signed zero and exponent boundaries.
   SPDX-License-Identifier: 0BSD */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
static unsigned checks, failures;
static double (*volatile call_trunc)(double) = trunc;
static void check(uint64_t input, uint64_t expected)
{
  union { double d; uint64_t u; } value, result;
  value.u = input; result.d = call_trunc(value.d);
  ++checks; if (result.u != expected) ++failures;
}
int main(void)
{
  unsigned sign, i;
  static const uint64_t inputs[] = {
    UINT64_C(0x0000000000000000), UINT64_C(0x0000000000000001),
    UINT64_C(0x000fffffffffffff), UINT64_C(0x0010000000000000),
    UINT64_C(0x3fefffffffffffff), UINT64_C(0x3ff0000000000000),
    UINT64_C(0x3fffffffffffffff), UINT64_C(0x4004000000000000),
    UINT64_C(0x432fffffffffffff), UINT64_C(0x4330000000000000),
    UINT64_C(0x7fefffffffffffff), UINT64_C(0x7ff0000000000000),
    UINT64_C(0x7ff8000000000123)
  };
  static const uint64_t expected[] = {
    0, 0, 0, 0, 0, UINT64_C(0x3ff0000000000000),
    UINT64_C(0x3ff0000000000000), UINT64_C(0x4000000000000000),
    UINT64_C(0x432ffffffffffffe), UINT64_C(0x4330000000000000),
    UINT64_C(0x7fefffffffffffff), UINT64_C(0x7ff0000000000000),
    UINT64_C(0x7ff8000000000123)
  };
  for (sign = 0; sign < 2; ++sign)
    for (i = 0; i < sizeof(inputs)/sizeof(inputs[0]); ++i)
      check(inputs[i] | ((uint64_t)sign << 63), expected[i] | ((uint64_t)sign << 63));
  /* Independent native ceil/floor oracle on exactly represented fractions. */
  for (i = 0; i < 2048; ++i) {
    double positive = (double)i / 16, negative = -positive;
    ++checks; if (call_trunc(positive) != floor(positive)) ++failures;
    ++checks; if (call_trunc(negative) != ceil(negative)) ++failures;
  }
  printf("trunc: %u checks, %u failures\n", checks, failures);
  return failures ? 1 : 0;
}
