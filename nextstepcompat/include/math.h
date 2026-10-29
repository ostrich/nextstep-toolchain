/* Native BSD math declarations hidden by the SDK's POSIX feature mode.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_MATH_H
#define NEXTSTEPCOMPAT_MATH_H
#include_next <math.h>
#ifdef __cplusplus
extern "C" {
#endif
/* These native BSD functions exist even in the SDK's POSIX feature mode. */
double acosh(double);
double asinh(double);
double atanh(double);
double hypot(double, double);
double cbrt(double);
double expm1(double);
double log1p(double);
double rint(double);
double fmin(double, double) __asm__("_ns33_fmin");
double fmax(double, double) __asm__("_ns33_fmax");
double log2(double) __asm__("_ns33_log2");
float floorf(float) __asm__("_ns33_floorf");
double round(double) __asm__("_ns33_round");
long lround(double) __asm__("_ns33_lround");
int finite(double);
double trunc(double);
extern __typeof__(exp) exp __asm__("_ns33_exp");
/* C99 floating constants, emitted directly in each target's native format. */
#ifndef NAN
#define NAN (__builtin_nanf(""))
#endif
#ifndef INFINITY
#define INFINITY (__builtin_inff())
#endif
#ifndef HUGE_VALF
#define HUGE_VALF (__builtin_huge_valf())
#endif
#ifndef HUGE_VALL
#define HUGE_VALL (__builtin_huge_vall())
#endif
#ifndef FP_NAN
#define FP_NAN 0
#define FP_INFINITE 1
#define FP_ZERO 2
#define FP_SUBNORMAL 3
#define FP_NORMAL 4
#endif
#if __FLT_EVAL_METHOD__ == 2
typedef long double float_t;
typedef long double double_t;
#elif __FLT_EVAL_METHOD__ == 1
typedef double float_t;
typedef double double_t;
#else
typedef float float_t;
typedef double double_t;
#endif
#ifndef isfinite
#define isfinite(x) __builtin_isfinite(x)
#endif
#ifndef isnormal
#define isnormal(x) __builtin_isnormal(x)
#endif
#ifndef isinf
#define isinf(x) __builtin_isinf(x)
#endif
#ifndef isnan
#define isnan(x) __builtin_isnan(x)
#endif
#ifndef signbit
#define signbit(x) __builtin_signbit(x)
#endif
#ifndef isgreater
#define isgreater(x, y) __builtin_isgreater((x), (y))
#endif
#ifndef isgreaterequal
#define isgreaterequal(x, y) __builtin_isgreaterequal((x), (y))
#endif
#ifndef isless
#define isless(x, y) __builtin_isless((x), (y))
#endif
#ifndef islessequal
#define islessequal(x, y) __builtin_islessequal((x), (y))
#endif
#ifndef islessgreater
#define islessgreater(x, y) __builtin_islessgreater((x), (y))
#endif
#ifndef isunordered
#define isunordered(x, y) __builtin_isunordered((x), (y))
#endif
#ifndef fpclassify
#define fpclassify(x) __builtin_fpclassify(FP_NAN, FP_INFINITE, FP_NORMAL, \
                                           FP_SUBNORMAL, FP_ZERO, (x))
#endif
#ifdef __cplusplus
}
#endif
#endif
