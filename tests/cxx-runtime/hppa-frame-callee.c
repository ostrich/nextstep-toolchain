/* SPDX-License-Identifier: 0BSD */
unsigned variable_frame(unsigned size)
{
  volatile unsigned char storage[size];
  register unsigned working __asm__("r3") = size;
  __asm__ volatile("" : "+r" (working));
  storage[0] = working;
  __asm__ volatile("" : : "r" (storage) : "memory");
  working += storage[0];
  __asm__ volatile("" : "+r" (working));
  return working;
}
