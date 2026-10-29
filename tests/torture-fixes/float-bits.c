/* Exercise 68040 conversion exception frames as well as compiler lowering. */
#include <stdint.h>
#include <stdlib.h>
static void convert(uint64_t bits, uint32_t expected)
{
 union { uint64_t u; double d; } input;
 union { uint32_t u; float f; } output;
 input.u = bits;
 volatile double value = input.d;
 output.f = (float)value;
 if (output.u != expected) abort();
}
int main(void)
{
 convert(UINT64_C(0x36a0000000000000), UINT32_C(1));
 convert(UINT64_C(0xb6a0000000000000), UINT32_C(0x80000001));
 convert(UINT64_C(0x0000000000007ff0), UINT32_C(0));
 convert(UINT64_C(0x8000000000007ff0), UINT32_C(0x80000000));
 return 0;
}
