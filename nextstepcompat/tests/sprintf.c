/* Unbounded formatter regressions. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
static int variadic(char *buffer, const char *format, ...) {
  int result;
  va_list arguments;
  va_start(arguments, format);
  result = vsprintf(buffer, format, arguments);
  va_end(arguments);
  return result;
}
int main(void) {
  char buffer[4096], input[2049];
  int result, failed = 0, count = -1;
  result = sprintf(buffer, "%.*g", 15, 123.456);
  if (result != 7 || strcmp(buffer, "123.456")) failed = 1;
  memset(input, 'x', sizeof input - 1); input[sizeof input - 1] = 0;
  result = variadic(buffer, "%s:%d:%#x%n", input, -123, 42, &count);
  if (result != 2058 || count != result || strlen(buffer) != (size_t)result ||
      strcmp(buffer + 2048, ":-123:0x2a")) failed = 1;
  result = sprintf(buffer, "%s", "");
  if (result || buffer[0]) failed = 1;
  result = variadic(buffer, "%2$d %1$s", "value", 42);
  if (result != 8 || strcmp(buffer, "42 value")) failed = 1;
  printf("sprintf adapters: %s\n", failed ? "FAIL" : "PASS");
  return failed;
}
