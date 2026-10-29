/* Diagnostic adapter only: avoid requiring vsnprintf to report its absence.
 * Upstream test bodies and assertions are unchanged. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdarg.h>
#include "test.h"
volatile int t_status = 0;
int t_printf(const char *format, ...)
{
    va_list args;
    int result;
    t_status = 1;
    va_start(args, format);
    result = vfprintf(stderr, format, args);
    va_end(args);
    return result;
}
