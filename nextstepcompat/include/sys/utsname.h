/* System identity from native Mach and BSD queries. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_UTSNAME_H
#define NEXTSTEPCOMPAT_SYS_UTSNAME_H
#include <standards.h>
#include_next <sys/utsname.h>
#ifdef __cplusplus
extern "C" {
#endif
int uname(struct utsname *) __asm__("_ns33_uname");
#ifdef __cplusplus
}
#endif
#endif
