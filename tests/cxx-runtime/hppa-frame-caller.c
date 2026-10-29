/* Reproduce loss of a callee-saved register across a variable-size frame.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
extern unsigned variable_frame(unsigned);
int main(void)
{
  register unsigned preserved __asm__("r3") = 0x13579bdfU;
  unsigned result;
  __asm__ volatile("" : "+r" (preserved));
  result = variable_frame(37);
  __asm__ volatile("" : "+r" (preserved));
  printf("hppa-frame: r3=%08x result=%u, %d failures\n", preserved, result,
         (preserved != 0x13579bdfU) + (result != 74));
  return preserved != 0x13579bdfU || result != 74;
}
