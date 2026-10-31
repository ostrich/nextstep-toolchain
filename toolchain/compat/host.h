/* Linux host declarations for the classic cctools programs. */
#ifndef NEXTSTEP_CCTOOLS_HOST_H
#define NEXTSTEP_CCTOOLS_HOST_H
#define _GNU_SOURCE 1
/* Historical Mach headers use Apple's arm64 spelling. */
#if defined(__aarch64__) && !defined(__arm64__)
#define __arm64__ 1
#endif
#include <errno.h>
#ifndef EFTYPE
#define EFTYPE EINVAL
#endif
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/time.h>
#ifndef __private_extern__
#define __private_extern__ __attribute__((visibility("hidden")))
#endif
#ifndef __dead2
#define __dead2 __attribute__((noreturn))
#endif
#ifndef __pure2
#define __pure2 __attribute__((const))
#endif
#ifndef __printflike
#define __printflike(a,b) __attribute__((format(printf,a,b)))
#endif
#ifndef MAXBSIZE
#define MAXBSIZE 65536
#endif
#ifndef MAP_FILE
#define MAP_FILE 0
#endif
void strmode(mode_t, char *);
size_t strlcpy(char *, const char *, size_t);
size_t strlcat(char *, const char *, size_t);
void *reallocf(void *, size_t);
#endif
