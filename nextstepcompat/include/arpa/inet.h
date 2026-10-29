/* IPv4 text conversion adapters. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_ARPA_INET_H
#define NEXTSTEPCOMPAT_ARPA_INET_H
#include <sys/socket.h>
#include <netinet/in.h>
#include_next <arpa/inet.h>
#ifdef __cplusplus
extern "C" {
#endif
int ns33_inet_pton(int, const char *, void *);
const char *ns33_inet_ntop(int, const void *, char *, socklen_t);
#ifdef __cplusplus
}
#endif
#define inet_pton ns33_inet_pton
#define inet_ntop ns33_inet_ntop
#endif
