/* Public adapters for NEXTSTEP 3.3 and OPENSTEP. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_H
#define NEXTSTEPCOMPAT_H
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <sys/types.h>
#include <time.h>
#include <ns33-multibyte.h>
#define NEXTSTEPCOMPAT_VERSION "0.1.0"
#ifdef __cplusplus
extern "C" {
#endif
char *ns33_strstr(const char *, const char *);
int ns33_memcmp(const void *, const void *, size_t);
int ns33_strcmp(const char *, const char *);
int ns33_strncmp(const char *, const char *, size_t);
size_t ns33_strftime(char *, size_t, const char *, const struct tm *);
long ns33_strtol(const char *, char **, int);
unsigned long ns33_strtoul(const char *, char **, int);
int ns33_printf(const char *, ...);
int ns33_vprintf(const char *, va_list);
int ns33_fprintf(FILE *, const char *, ...);
int ns33_vfprintf(FILE *, const char *, va_list);
size_t ns33_fwrite(const void *, size_t, size_t, FILE *);
int ns33_ungetc(int, FILE *);
int ns33_sscanf(const char *, const char *, ...);
int ns33_vsscanf(const char *, const char *, va_list);
int ns33_fscanf(FILE *, const char *, ...);
int ns33_vfscanf(FILE *, const char *, va_list);
int ns33_scanf(const char *, ...);
int ns33_vscanf(const char *, va_list);
int ns33_getgroups(int, gid_t *);
int ns33_remove(const char *);
int ns33_strcoll(const char *, const char *);
size_t ns33_strxfrm(char *, const char *, size_t);
char *ns33_strerror(int);
int ns33_strerror_r(int, char *, size_t);
char *ns33_realpath(const char *, char *);
double ns33_strtod(const char *, char **);
#ifdef __cplusplus
}
#endif
#endif
