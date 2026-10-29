/* writev does not modify its iovec array. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_UIO_H
#define NEXTSTEPCOMPAT_SYS_UIO_H
#include <sys/types.h>
#define writev ns33_sdk_writev_declaration
#include_next <sys/uio.h>
#undef writev
#ifdef __cplusplus
extern "C" {
#endif
ssize_t writev(int, const struct iovec *, int);
#ifdef __cplusplus
}
#endif
#endif
