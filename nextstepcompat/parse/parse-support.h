/* String-only input and exact binary scaling for musl's floating scanner.
   SPDX-License-Identifier: 0BSD */
#include <stddef.h>

struct parse_stream {
  const unsigned char *start, *cursor;
  int failed;
};

/* The scanner reads the terminating NUL as its lookahead character, then
   pushes it back. It never advances beyond it on the string-only path. */
#define shgetc(f) ((int)*(f)->cursor++)
#define shunget(f) ((void)((f)->cursor--))
#define shlim(f, limit) ((void)((f)->failed = 1))
#include "binary-scale.h"
