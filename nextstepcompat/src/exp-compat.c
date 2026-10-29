/* The original finite-input algorithm mishandles infinite inputs.
   SPDX-License-Identifier: 0BSD */
#include <math.h>
extern double ns33_native_exp(double) __asm__("_exp");

double ns33_exp(double value)
{
  if (__builtin_isinf(value)) return value > 0 ? value : 0.0;
  return ns33_native_exp(value);
}
