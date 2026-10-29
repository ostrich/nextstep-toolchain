/* Internet address types matching the native 32-bit ABI. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_NETINET_IN_H
#define NEXTSTEPCOMPAT_NETINET_IN_H
#include <sys/types.h>
#include <sys/socket.h>
#include <stdint.h>
#include <endian.h>
#include_next <netinet/in.h>
typedef uint32_t in_addr_t;
typedef uint16_t in_port_t;
/* These layouts support address parsing and certificate data, not native
   IPv6 transport. The original socket ABI uses a 16-bit family field. */
struct in6_addr { unsigned char s6_addr[16]; };
struct sockaddr_in6 {
  unsigned short sin6_family;
  in_port_t sin6_port;
  uint32_t sin6_flowinfo;
  struct in6_addr sin6_addr;
  uint32_t sin6_scope_id;
};
#define INET6_ADDRSTRLEN 46
#define IN6_IS_ADDR_V4MAPPED(a) \
  (!__builtin_memcmp((a)->s6_addr,"\0\0\0\0\0\0\0\0\0\0\xff\xff",12))
#ifndef INET_ADDRSTRLEN
#define INET_ADDRSTRLEN 16
#endif
#endif
