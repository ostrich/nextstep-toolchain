/* Choose SDK feature visibility before its guarded type declarations.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_STANDARDS_H
#define NEXTSTEPCOMPAT_STANDARDS_H
#ifndef _POSIX_SOURCE
#define _POSIX_SOURCE 1
#endif
#include_next <standards.h>
/* NeXT's POSIX selector defines this reserved GCC macro without a value.
   Preserve its existing feature-selection effect, but make numeric tests in
   modern headers and applications valid. Strict language modes already use 1. */
#ifdef __STRICT_ANSI__
#undef __STRICT_ANSI__
#define __STRICT_ANSI__ 1
#endif
#endif
