/* IPv4 resolver adapters. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_NETDB_H
#define NEXTSTEPCOMPAT_NETDB_H
#include <sys/socket.h>
#include <stddef.h>
#include_next <netdb.h>
#define AI_PASSIVE 1
#define AI_CANONNAME 2
#define AI_NUMERICHOST 4
#define AI_NUMERICSERV 8
#define AI_ADDRCONFIG 16
#define NI_NUMERICHOST 1
#define NI_NUMERICSERV 2
#define NI_NAMEREQD 4
#define NI_DGRAM 8
#define NI_MAXHOST 1025
#define NI_MAXSERV 32
#define EAI_BADFLAGS -1
#define EAI_NONAME -2
#define EAI_AGAIN -3
#define EAI_FAIL -4
#define EAI_FAMILY -6
#define EAI_SOCKTYPE -7
#define EAI_SERVICE -8
#define EAI_MEMORY -10
#define EAI_SYSTEM -11
#define EAI_OVERFLOW -12
struct addrinfo {
  int ai_flags, ai_family, ai_socktype, ai_protocol;
  socklen_t ai_addrlen;
  char *ai_canonname;
  struct sockaddr *ai_addr;
  struct addrinfo *ai_next;
};
#ifdef __cplusplus
extern "C" {
#endif
int innetgr(const char *, const char *, const char *, const char *);
int ns33_getaddrinfo(const char *, const char *, const struct addrinfo *, struct addrinfo **);
void ns33_freeaddrinfo(struct addrinfo *);
const char *ns33_gai_strerror(int);
int ns33_getnameinfo(const struct sockaddr *, socklen_t, char *, socklen_t, char *, socklen_t, int);
#ifdef __cplusplus
}
#endif
#define getaddrinfo ns33_getaddrinfo
#define freeaddrinfo ns33_freeaddrinfo
#define gai_strerror ns33_gai_strerror
#define getnameinfo ns33_getnameinfo
#endif
