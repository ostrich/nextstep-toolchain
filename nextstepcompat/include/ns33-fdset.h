/* Repair the native FD_ZERO macro using ISO C facilities.
   Include after the native fd_set declaration. SPDX-License-Identifier: 0BSD */
#if !defined(KERNEL) && defined(FD_ZERO)
#ifndef NEXTSTEPCOMPAT_FDSET_H
#define NEXTSTEPCOMPAT_FDSET_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
void *memset(void *, int, size_t);
#ifdef __cplusplus
}
#endif
#undef FD_ZERO
#define FD_ZERO(set) ((void)memset((set), 0, sizeof(*(set))))
#endif
#endif
