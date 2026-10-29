/* Native socket ABI additions. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_SOCKET_H
#define NEXTSTEPCOMPAT_SYS_SOCKET_H
#include <sys/types.h>
#include_next <sys/socket.h>
/* Data-only IPv6 identifier, outside the native kernel's domain table.
   Its presence does not imply IPv6 socket support. */
#ifndef AF_INET6
#define AF_INET6 24
#define PF_INET6 AF_INET6
#define NS33_IPV6_DATA_ONLY 1
#if AF_INET6 < AF_MAX
#error Review the data-only IPv6 family value for this SDK
#endif
#endif
struct __attribute__((aligned(__alignof__(unsigned long long)))) sockaddr_storage {
  unsigned short ss_family;
  unsigned char __ns33_padding[126];
};
/* The original socket calls take int lengths and int * result lengths. */
typedef int socklen_t;
#ifdef __cplusplus
extern "C" {
#endif
int shutdown(int, int);
#ifdef __cplusplus
}
#endif
#ifndef SHUT_RD
#define SHUT_RD 0
#define SHUT_WR 1
#define SHUT_RDWR 2
#endif
#endif
