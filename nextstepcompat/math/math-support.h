/* Minimal binary64 support for the pinned musl log2 implementation.
   SPDX-License-Identifier: MIT */
#ifndef NS33_MATH_SUPPORT_H
#define NS33_MATH_SUPPORT_H
#include <math.h>
#include <stdint.h>
#include <float.h>
#include <errno.h>
_Static_assert(sizeof(double) == 8 && DBL_MANT_DIG == 53 &&
               DBL_MAX_EXP == 1024, "log2 requires IEEE binary64");
#define WANT_ROUNDING 1
#define predict_false(x) __builtin_expect(!!(x), 0)
#define asuint64(f) ((union { double f64; uint64_t u64; }){ .f64 = (f) }).u64
#define asdouble(i) ((union { double f64; uint64_t u64; }){ .u64 = (i) }).f64
static inline double eval_as_double(double x)
{
  double y = x;
  return y;
}
static inline double ns33_math_divzero(uint32_t sign)
{
  volatile double numerator = sign ? -1.0 : 1.0;
  errno = ERANGE;
  return numerator / 0.0;
}
static inline double ns33_math_invalid(double x)
{
  if (!isnan(x)) errno = EDOM;
  return (x - x) / (x - x);
}
#endif
