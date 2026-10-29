/* Modern status-pointer spelling for the native BSD wait3 ABI.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_WAIT_H
#define NEXTSTEPCOMPAT_SYS_WAIT_H
#define wait3 ns33_native_wait3_declaration
#include_next <sys/wait.h>
#undef wait3
#ifdef __cplusplus
extern "C" {
#endif
struct rusage;
/* union wait and int carry the same native status word. */
int wait3(int *, int, struct rusage *) __asm__("_wait3");
/* libsys exports wait4 even though the SDK omits its user declaration. */
pid_t wait4(pid_t, int *, int, struct rusage *);
#ifdef __cplusplus
}
#endif
#endif
