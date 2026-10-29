/* Exact binary scaling shared by string and stream scanners.
   SPDX-License-Identifier: 0BSD */
#ifndef INFINITY
#define INFINITY (__builtin_inff())
#endif
#ifndef NAN
#define NAN (__builtin_nanf(""))
#endif

static long double parse_power(int exponent)
{
  unsigned magnitude = exponent < 0 ? -exponent : exponent;
  long double value = 1, factor = exponent < 0 ? 0.5L : 2.0L;
  while (magnitude) {
    if (magnitude & 1) value *= factor;
    magnitude >>= 1;
    if (magnitude) factor *= factor;
  }
  return value;
}

/* Keep the final underflowing multiplication separate from the exact normal
   scaling, so subnormals round once. No assumptions about x87/68881 layout. */
static long double parse_scale(long double value, int exponent)
{
  const int finite_nonzero = value != 0 && __builtin_isfinite(value);
  const int high = LDBL_MAX_EXP - 1;
  const int low = LDBL_MIN_EXP - 1;
  if (exponent > high) {
    value *= parse_power(high); exponent -= high;
    if (exponent > high) {
      value *= parse_power(high); exponent -= high;
      if (exponent > high) exponent = high;
    }
  } else if (exponent < low) {
    value *= parse_power(low + LDBL_MANT_DIG);
    exponent -= low + LDBL_MANT_DIG;
    if (exponent < low) {
      value *= parse_power(low + LDBL_MANT_DIG);
      exponent -= low + LDBL_MANT_DIG;
      if (exponent < low) exponent = low;
    }
  }
  {
    long double result = value * parse_power(exponent);
    if (finite_nonzero &&
        (!__builtin_isfinite(result) || result == 0 ||
         __builtin_fabsl(result) < LDBL_MIN)) errno = ERANGE;
    return result;
  }
}

/* floatscan only requests remainder modulo a positive power of two. Binary
   subtraction is exact here and avoids narrowing long double through libc. */
static long double parse_remainder(long double value, long double divisor)
{
  int negative = __builtin_signbit(value);
  long double scale;
  if (negative) value = -value;
  scale = divisor;
  while (scale <= value * 0.5L) scale *= 2;
  while (scale >= divisor) {
    if (value >= scale) value -= scale;
    scale *= 0.5L;
  }
  return negative ? -value : value;
}

#define scalbnl parse_scale
#define scalbn(value, exponent) parse_scale((value), (exponent))
#define fmodl parse_remainder
#define fabsl(value) __builtin_fabsl(value)
#define copysignl(value, sign) __builtin_copysignl((value), (sign))
