/* Truncate IEEE binary64 toward zero without depending on rounding mode.
   NEXTSTEP NIHS stores double as binary64 on all four architectures.
   SPDX-License-Identifier: 0BSD */
#include <stdint.h>
double trunc(double value)
{
  union { double d; uint64_t u; } bits;
  unsigned exponent;
  bits.d = value;
  exponent = (unsigned)((bits.u >> 52) & 0x7ff);
  /* Large finite values are already integral. Preserve infinities and NaNs. */
  if (exponent >= 1023 + 52) return value;
  if (exponent < 1023)
    bits.u &= UINT64_C(0x8000000000000000);
  else
    bits.u &= ~((UINT64_C(1) << (1023 + 52 - exponent)) - 1);
  return bits.d;
}
