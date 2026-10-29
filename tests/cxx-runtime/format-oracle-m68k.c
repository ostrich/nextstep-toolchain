/* Linux x87-host oracle for the Motorola extended-precision formatter.
   SPDX-License-Identifier: 0BSD */
#include <float.h>
#if LDBL_MANT_DIG != 64 || LDBL_MAX_EXP != 16384 || LDBL_MIN_EXP != -16381
#error This oracle requires an x87 extended-precision host
#endif
/* Motorola allows an exponent-zero normal number. Its minimum normal is
   half the x87 minimum; both formats otherwise use the same value precision
   and maximum exponent for the tested corpus. */
#undef LDBL_MIN
#define LDBL_MIN 0x1p-16383L
#include "format.c"
