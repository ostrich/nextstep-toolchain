/* Select POSIX types before the SDK's one-shot type guard is evaluated.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_TYPES_H
#define NEXTSTEPCOMPAT_SYS_TYPES_H
#include <standards.h>
#include_next <sys/types.h>
/* The SDK macro calls undeclared BSD bzero in POSIX mode. */
#ifdef FD_ZERO
#undef FD_ZERO
#define FD_ZERO(set) ((void)__builtin_memset((set), 0, sizeof(*(set))))
#endif
#endif
