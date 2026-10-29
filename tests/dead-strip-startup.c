/* Keep classic startup metadata while eliminating genuinely unused code.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
/* Give the linker function-sized atoms for the elimination assertion. */
__asm__(".subsections_via_symbols");
static volatile int initialized;
static void initialize(void) __attribute__((constructor));
static void initialize(void) { initialized = 19; }
int ns33_unreachable_dead_strip_probe(void) { return 987654; }
int main(void)
{
  if (initialized != 19) return 1;
  puts("PASS dead-strip startup initialization");
  return 0;
}
