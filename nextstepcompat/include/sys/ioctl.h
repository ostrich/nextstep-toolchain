/* The original ioctl header supplies requests but omits the function.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_IOCTL_H
#define NEXTSTEPCOMPAT_IOCTL_H
#include_next <sys/ioctl.h>
#ifdef __cplusplus
extern "C" {
#endif
int ioctl(int, long, ...);
#ifdef __cplusplus
}
#endif
#endif
