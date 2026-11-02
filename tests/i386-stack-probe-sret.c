/* The NeXT/i386 hidden aggregate-result pointer is live in EBX on entry.
   Looped stack probes must preserve it, including for local register-argument
   functions.  Compile with -O1 -fstack-clash-protection.  */
#include <stdio.h>
#include <stdint.h>

struct result { unsigned char bytes[1460]; } __attribute__((aligned(4)));

__attribute__((noinline,noclone))
static struct result aggregate(int a, int b, int c)
{
  volatile unsigned char frame[65536];
  struct result value;
  unsigned int i;
  frame[0] = a;
  frame[sizeof(frame) - 1] = b;
  __asm__ volatile ("" : : "m"(frame) : "memory");
  for (i = 0; i < sizeof(value); ++i)
    value.bytes[i] = (unsigned char)(a + b + c + i);
  return value;
}

__attribute__((noinline,noclone))
static unsigned int scalar(int a, int b, int c)
{
  volatile unsigned char frame[65536];
  frame[0] = a;
  frame[sizeof(frame) - 1] = b;
  __asm__ volatile ("" : : "m"(frame) : "memory");
  return a + b + c + frame[0] + frame[sizeof(frame) - 1];
}

int main(int argc, char **argv)
{
  struct result value;
  unsigned int i, round, failures = 0;
  (void)argv;
  for (round = 0; round < 3; ++round) {
    int a = argc + round, b = argc + round + 3, c = argc + round + 9;
    value = aggregate(a, b, c);
    for (i = 0; i < sizeof(value); ++i)
      if (value.bytes[i] != (unsigned char)(a + b + c + i)) {
        printf("FAIL aggregate round %u offset %u: expected %u, got %u\n",
               round, i, (unsigned char)(a + b + c + i), value.bytes[i]);
        ++failures;
        break;
      }
    if (scalar(a, b, c) != (unsigned int)(2 * a + 2 * b + c)) {
      printf("FAIL scalar round %u\n", round);
      ++failures;
    }
  }
  if (failures) return 1;
  puts("PASS looped stack probes: aggregate results and scalar arguments");
  return 0;
}
