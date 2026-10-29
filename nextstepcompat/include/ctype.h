/* BSD ASCII extensions omitted by the native POSIX header mode.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_CTYPE_H
#define NEXTSTEPCOMPAT_CTYPE_H
#include_next <ctype.h>
#undef isascii
#undef toascii
#ifdef __cplusplus
extern "C" {
#endif
int isascii(int) __asm__("_ns33_isascii");
int toascii(int) __asm__("_ns33_toascii");
#ifdef __cplusplus
}
#endif
#define isascii(c) ((unsigned int)(c) <= 127)
#define toascii(c) ((int)((c) & 127))
#endif
