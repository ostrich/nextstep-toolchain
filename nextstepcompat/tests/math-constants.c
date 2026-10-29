/* C99 floating constant types and runtime representation. SPDX-License-Identifier: 0BSD */
#include <math.h>
#include <float.h>
#include <stdio.h>
#include <string.h>
#ifdef __cplusplus
static_assert(sizeof(NAN) == sizeof(float), "NAN type");
static_assert(sizeof(INFINITY) == sizeof(float), "INFINITY type");
static_assert(sizeof(HUGE_VALF) == sizeof(float), "HUGE_VALF type");
static_assert(sizeof(HUGE_VALL) == sizeof(long double), "HUGE_VALL type");
#else
_Static_assert(sizeof(NAN) == sizeof(float), "NAN type");
_Static_assert(sizeof(INFINITY) == sizeof(float), "INFINITY type");
_Static_assert(sizeof(HUGE_VALF) == sizeof(float), "HUGE_VALF type");
_Static_assert(sizeof(HUGE_VALL) == sizeof(long double), "HUGE_VALL type");
#endif
int main(void)
{
 volatile float nan_value = NAN, inf_value = INFINITY, huge_float = HUGE_VALF;
 volatile long double huge_long = HUGE_VALL;
 float n = nan_value, i = inf_value;
 unsigned int nbits, ibits;
 memcpy(&nbits, &n, sizeof(nbits)); memcpy(&ibits, &i, sizeof(ibits));
 if (!isnan(nan_value) || !isinf(inf_value) || !isinf(huge_float) ||
     !isinf(huge_long) || !(inf_value > FLT_MAX) || ibits != 0x7f800000U ||
     (nbits & 0x7f800000U) != 0x7f800000U || !(nbits & 0x007fffffU)) return 1;
 puts("PASS typed C99 math constants and runtime IEEE representations");
 return 0;
}
