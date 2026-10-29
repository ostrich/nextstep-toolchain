/* ISO C interfaces over the pre-ISO NEXTSTEP string header.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_STRING_H
#define NEXTSTEPCOMPAT_STRING_H
/* Hide the incompatible legacy three-argument declaration. */
#define strcoll ns33_native_strcoll
#define strerror ns33_native_strerror
#include_next <string.h>
#undef strcoll
#undef strerror
#ifdef __cplusplus
extern "C" {
#endif
char *strstr(const char *, const char *) __asm__("_ns33_strstr");
int memcmp(const void *, const void *, size_t) __asm__("_ns33_memcmp");
int strcmp(const char *, const char *) __asm__("_ns33_strcmp");
int strncmp(const char *, const char *, size_t) __asm__("_ns33_strncmp");
void explicit_bzero(void *, size_t);
char *strsignal(int) __asm__("_ns33_strsignal");
char *stpcpy(char *, const char *) __asm__("_ns33_stpcpy");
char *strcasestr(const char *, const char *) __asm__("_ns33_strcasestr");
char *strdup(const char *);
char *strndup(const char *, size_t);
size_t strnlen(const char *, size_t);
void *memccpy(void *, const void *, int, size_t);
char *strsep(char **, const char *);
char *strtok_r(char *, const char *, char **);
char *ns33_native_strerror(int) __asm__("_strerror");
char *strerror(int) __asm__("_ns33_strerror");
int strerror_r(int, char *, size_t) __asm__("_ns33_strerror_r");
int strcoll(const char *, const char *) __asm__("_ns33_strcoll");
size_t strxfrm(char *, const char *, size_t) __asm__("_ns33_strxfrm");
#ifdef __cplusplus
}
#endif
#endif
