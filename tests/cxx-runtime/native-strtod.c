/* Observe the original library's parsing contract; not a conformance pass.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
/* Bypass the compatibility header's private symbol on purpose. */
extern double original_strtod(const char *, char **) __asm__("_strtod");
int main(void)
{
  static const char *const inputs[] = {"1.25tail", " 1.25 rest", "0x1.8p+1", "inf", "nan"};
  double (*volatile parse)(const char *, char **) = original_strtod;
  unsigned i;
  for (i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i) {
    char *end, text[80];
    double value;
    int saved;
    errno = 73;
    value = parse(inputs[i], &end); saved = errno;
    snprintf(text, sizeof(text), "%.17g", value);
    printf("native strtod: '%s' value=%s end=%u errno=%d\n", inputs[i], text,
           (unsigned)(end - inputs[i]), saved);
  }
  return 0;
}
