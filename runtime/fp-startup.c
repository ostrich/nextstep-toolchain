/* Floating-point environment required by the modern compiler.
   SPDX-License-Identifier: 0BSD */
void __nextstep_initialize_floating_point(void)
{
#if defined(__i386__)
  unsigned short control;
  __asm__ volatile("fnstcw %0" : "=m"(control));
  /* Preserve exception masks and rounding, and select the 64-bit significand
     assumed by GCC's 80-bit long double. Native startup selects 53 bits. */
  control = (control & ~0x0300) | 0x0300;
  __asm__ volatile("fldcw %0" : : "m"(control));
#elif defined(__mc68000__)
  unsigned long control;
  __asm__ volatile("fmovel fpcr,%0" : "=d"(control));
  /* Motorola double precision also limits the exponent range. GCC's
     extended type requires the native 80-bit significand/exponent mode. */
  control &= ~0x00c0UL;
  __asm__ volatile("fmovel %0,fpcr" : : "d"(control));
#endif
}

static void __attribute__((constructor)) nextstep_runtime_startup(void)
{
  __nextstep_initialize_floating_point();
}

