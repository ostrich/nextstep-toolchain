/* A private scanner stream, not a replacement for native FILE.
   SPDX-License-Identifier: 0BSD */
#ifndef NS33_SCAN_SUPPORT_H
#define NS33_SCAN_SUPPORT_H
#include <stdio.h>
#include <sys/types.h>
#include <stdarg.h>
struct ns33_scan_stream {
  unsigned char *buf, *rpos, *rend, *shend;
  off_t shcnt, shlim;
  FILE *native;
  unsigned char scratch[2];
};
int ns33_scan_read(struct ns33_scan_stream *);
void ns33_scan_limit(struct ns33_scan_stream *, off_t);
int ns33_scan_get(struct ns33_scan_stream *);
unsigned long long ns33_scan_integer(struct ns33_scan_stream *, unsigned, int, unsigned long long);
long double ns33_scan_float(struct ns33_scan_stream *, int, int);
int ns33_scan_core(struct ns33_scan_stream *, const char *, va_list);
#endif
