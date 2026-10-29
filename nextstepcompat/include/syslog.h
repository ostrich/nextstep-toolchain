/* The native syslog header omits its existing va_list entry point.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYSLOG_H
#define NEXTSTEPCOMPAT_SYSLOG_H
#include <stdarg.h>
#include_next <syslog.h>
#ifdef __cplusplus
extern "C" {
#endif
void vsyslog(int, const char *, va_list);
#ifdef __cplusplus
}
#endif
#endif
