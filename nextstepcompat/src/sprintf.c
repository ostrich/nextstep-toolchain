/* Unbounded formatting through the maintained formatter. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdarg.h>
#include <limits.h>

int ns33_vsprintf(char *buffer, const char *format, va_list arguments)
{
  return vsnprintf(buffer, INT_MAX, format, arguments);
}

int ns33_sprintf(char *buffer, const char *format, ...)
{
  va_list arguments;
  int result;
  va_start(arguments, format);
  result = ns33_vsprintf(buffer, format, arguments);
  va_end(arguments);
  return result;
}
