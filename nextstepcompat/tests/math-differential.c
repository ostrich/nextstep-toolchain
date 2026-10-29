/* Deterministic host-libm comparison, supplementing high-precision vectors.
   SPDX-License-Identifier: 0BSD */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
extern double ns33_log2(double);
static uint64_t bits(double x)
{
  union { double d; uint64_t u; } v;
  v.d = x;
  return v.u;
}
int main(void)
{
  uint64_t seed = UINT64_C(0x3320260526), maximum = 0;
  double (*volatile reference)(double) = log2;
  unsigned i, failures = 0;
  for (i = 0; i < 1000000; i++) {
    union { double d; uint64_t u; } v;
    double actual, expected;
    uint64_t a, b, distance;
    seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
    v.u = seed & UINT64_C(0x7fffffffffffffff);
    if ((v.u >> 52) == 0x7ff) v.u &= ~UINT64_C(0x0010000000000000);
    if (v.u == 0) v.u = 1;
    actual = ns33_log2(v.d);
    expected = reference(v.d);
    a = bits(actual); b = bits(expected);
    distance = a > b ? a - b : b - a;
    if (distance > maximum) maximum = distance;
    if (!isfinite(actual) || distance > 1) {
      if (failures++ < 10)
        printf("FAIL log2(%a): %a versus %a\n", v.d, actual, expected);
    }
  }
  printf("%s log2 differential: 1000000 positive finite bit patterns, max %u ULP, %u failures\n",
         failures ? "FAIL" : "PASS", (unsigned)maximum, failures);
  return failures != 0;
}
