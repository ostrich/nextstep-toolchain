/* Separate parser, constant, conversion and multiply behavior.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>

static void show(const char *name, long double value)
{
  unsigned i;
  unsigned char *bytes = (unsigned char *)&value;
  char text[128];
  snprintf(text, sizeof(text), "%La", value);
  printf("%s: %s isinf=%d isnan=%d bytes=", name, text,
         !!isinf(value), !!isnan(value));
  for (i = 0; i < sizeof(value); ++i) printf("%02x", bytes[i]);
  printf("\n");
}

int main(void)
{
  volatile float single = __builtin_inff();
  volatile long double large = LDBL_MAX;
  volatile int sign = -1;
  char *end;
  show("literal extended", __builtin_infl());
  show("widened single", single);
  show("single multiply", single * sign);
  show("extended multiply", (long double)single * sign);
  show("overflow", large * large);
  show("parsed extended", strtold("inf", &end));
  printf("extended consumed=%d\n", (int)*end);
  show("parsed double", strtod("inf", &end));
  printf("double consumed=%d\n", (int)*end);
  return 0;
}
