/* SPDX-License-Identifier: 0BSD */
#include <stdio.h>
static volatile long double numerator = 1.0L;
int main(void)
{
#if defined(__i386__)
  unsigned short control;
  __asm__ volatile("fnstcw %0" : "=m"(control));
  printf("FPU_CONTROL:%04x\n", control);
#elif defined(__mc68000__)
  unsigned long control;
  __asm__ volatile("fmovel fpcr,%0" : "=d"(control));
  printf("FPU_CONTROL:%08lx\n", control);
#endif
  long double third = numerator / 3.0L;
  printf("EXTENDED_GREATER:%d\n", third > (long double)(1.0 / 3.0));
  return 0;
}
