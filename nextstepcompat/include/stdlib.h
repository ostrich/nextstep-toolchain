/* C99 integer conversion and modern realpath over the original SDK.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_STDLIB_H
#define NEXTSTEPCOMPAT_STDLIB_H
#include_next <stdlib.h>
#ifdef __cplusplus
extern "C" {
#endif
#ifndef malloc
void *malloc(size_t) __asm__("_ns33_malloc");
#endif
#ifndef calloc
void *calloc(size_t, size_t) __asm__("_ns33_calloc");
#endif
#ifndef realloc
void *realloc(void *, size_t) __asm__("_ns33_realloc");
#endif
/* Native zone-allocation size, also valid for the checked front ends. */
size_t malloc_size(void *);
long strtol(const char *, char **, int) __asm__("_ns33_strtol");
unsigned long strtoul(const char *, char **, int) __asm__("_ns33_strtoul");
long long strtoll(const char *, char **, int);
unsigned long long strtoull(const char *, char **, int);
long long atoll(const char *);
typedef struct { long long quot, rem; } lldiv_t;
long long llabs(long long);
lldiv_t lldiv(long long, long long);
void _Exit(int) __attribute__((__noreturn__, __nothrow__));
float strtof(const char *, char **);
double strtod(const char *, char **) __asm__("_ns33_strtod");
long double strtold(const char *, char **);
char *realpath(const char *, char *) __asm__("_ns33_realpath");
char *mktemp(char *);
int mkstemp(char *);
int putenv(char *);
int setenv(const char *, const char *, int);
int unsetenv(const char *);
#ifdef __cplusplus
}
#endif
#include <ns33-multibyte.h>
#ifdef __cplusplus
extern "C" {
#endif
int mblen(const char *, size_t) __asm__("_ns33_mblen");
int mbtowc(wchar_t *, const char *, size_t) __asm__("_ns33_mbtowc");
int wctomb(char *, wchar_t) __asm__("_ns33_wctomb");
size_t mbstowcs(wchar_t *, const char *, size_t) __asm__("_ns33_mbstowcs");
size_t wcstombs(char *, const wchar_t *, size_t) __asm__("_ns33_wcstombs");
#ifdef __cplusplus
}
#endif
#undef MB_CUR_MAX
#define MB_CUR_MAX (ns33_mb_cur_max())
#endif
