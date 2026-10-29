/* Single-byte conversion ABI; reserved state permits later encodings.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_MULTIBYTE_H
#define NEXTSTEPCOMPAT_MULTIBYTE_H
#include <stddef.h>
#ifndef _WINT_T
#define _WINT_T
typedef unsigned int wint_t;
#endif
typedef struct ns33_mbstate {
    unsigned int state;
    unsigned int reserved[3];
} mbstate_t;
#ifndef WEOF
#define WEOF ((wint_t) - 1)
#endif
#ifndef WCHAR_MIN
#define WCHAR_MIN 0
#endif
#ifndef WCHAR_MAX
#define WCHAR_MAX __WCHAR_MAX__
#endif
#ifdef __cplusplus
extern "C" {
#endif
size_t ns33_mb_cur_max(void);
int ns33_mblen(const char *, size_t);
int ns33_mbtowc(wchar_t *, const char *, size_t);
int ns33_wctomb(char *, wchar_t);
size_t ns33_mbstowcs(wchar_t *, const char *, size_t);
size_t ns33_wcstombs(char *, const wchar_t *, size_t);
#ifdef __cplusplus
}
#endif
#endif
