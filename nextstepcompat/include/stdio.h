/* C++ requires FILE to be a type name, rather than a macro.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_STDIO_H
#define NEXTSTEPCOMPAT_STDIO_H
#include <stdarg.h>
#include <sys/types.h>
#include_next <stdio.h>
#ifdef FILE
#undef FILE
typedef struct _iobuf FILE;
#endif
#ifdef __cplusplus
extern "C" {
#endif
FILE *fopen(const char *, const char *) __asm__("_ns33_fopen");
FILE *fdopen(int, const char *) __asm__("_ns33_fdopen");
FILE *freopen(const char *, const char *, FILE *) __asm__("_ns33_freopen");
int printf(const char *, ...) __asm__("_ns33_printf");
int vprintf(const char *, va_list) __asm__("_ns33_vprintf");
int fprintf(FILE *, const char *, ...) __asm__("_ns33_fprintf");
int vfprintf(FILE *, const char *, va_list) __asm__("_ns33_vfprintf");
size_t fwrite(const void *, size_t, size_t, FILE *) __asm__("_ns33_fwrite");
int ungetc(int, FILE *) __asm__("_ns33_ungetc");
int fflush(FILE *) __asm__("_ns33_fflush");
int sscanf(const char *, const char *, ...) __asm__("_ns33_sscanf");
int vsscanf(const char *, const char *, va_list) __asm__("_ns33_vsscanf");
int fscanf(FILE *, const char *, ...) __asm__("_ns33_fscanf");
int vfscanf(FILE *, const char *, va_list) __asm__("_ns33_vfscanf");
int scanf(const char *, ...) __asm__("_ns33_scanf");
int vscanf(const char *, va_list) __asm__("_ns33_vscanf");
int remove(const char *) __asm__("_ns33_remove");
int asprintf(char **, const char *, ...);
int vasprintf(char **, const char *, va_list);
int sprintf(char *, const char *, ...) __asm__("_ns33_sprintf");
int vsprintf(char *, const char *, va_list) __asm__("_ns33_vsprintf");
int snprintf(char *, size_t, const char *, ...);
int vsnprintf(char *, size_t, const char *, va_list);
ssize_t getdelim(char **, size_t *, int, FILE *);
ssize_t getline(char **, size_t *, FILE *);
#ifdef __cplusplus
}
#endif
#endif
