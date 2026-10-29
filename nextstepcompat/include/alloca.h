/* GCC supplies stack allocation; there is no external alloca function.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_ALLOCA_H
#define NEXTSTEPCOMPAT_ALLOCA_H
#include <stddef.h>
#ifndef alloca
#define alloca(size) __builtin_alloca(size)
#endif
#endif
