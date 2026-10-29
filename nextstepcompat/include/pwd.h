/* Native BSD account enumeration, hidden in the POSIX namespace.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_PWD_H
#define NEXTSTEPCOMPAT_PWD_H
#include_next <pwd.h>
#ifdef __cplusplus
extern "C" {
#endif
struct passwd *getpwent(void);
void setpwent(void);
void endpwent(void);
#ifdef __cplusplus
}
#endif
#endif
