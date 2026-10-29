/* Basic C runtime checks. Expected vectors are generated independently by Python. */
#include <stdio.h>
typedef unsigned long long U;
typedef long long S;
#include "runtime-vectors.h"
static int checks, failures;
static void check(int good, const char *name, int row)
{
  ++checks;
  if (!good) {
    if (failures < 12) printf("FAIL %s row %d\n", name, row);
    ++failures;
  }
}
int main(void)
{
  unsigned i;
  for (i = 0; i < sizeof(vectors) / sizeof(vectors[0]); ++i) {
    volatile U a = vectors[i].a, b = vectors[i].b;
    volatile unsigned shift = vectors[i].shift;
    volatile S s = (S)a, t = (S)b;
    check(a * b == vectors[i].mul, "mul", i);
    check(a / b == vectors[i].div, "udiv", i);
    check(a % b == vectors[i].rem, "umod", i);
    check((a << shift) == vectors[i].left, "left", i);
    check((a >> shift) == vectors[i].right, "right", i);
    check((s >> shift) == vectors[i].signed_right, "signed right", i);
    check(s / t == vectors[i].signed_div, "sdiv", i);
    check(s % t == vectors[i].signed_rem, "smod", i);
    check(__builtin_popcountll(a) == vectors[i].popcount, "popcount", i);
    check(__builtin_clzll(a) == vectors[i].clz, "clz", i);
    check(__builtin_ctzll(a) == vectors[i].ctz, "ctz", i);
    check(__builtin_parityll(a) == (vectors[i].popcount & 1), "parity", i);
    check(__builtin_bswap64(a) == vectors[i].swapped, "bswap", i);
  }
  for (i = 0; i < 64; ++i) {
    volatile U u = (1ULL << i) + (i && i < 24 ? 1 : 0);
    volatile S s = i == 63 ? (S)u : -(S)u;
    volatile float fu = (float)u, fs = (float)s;
    volatile double du = (double)u, ds = (double)s;
    volatile long double lu = (long double)u, ls = (long double)s;
    check((U)fu == u, "float unsigned roundtrip", i);
    check((S)fs == s, "float signed roundtrip", i);
    check((U)du == u, "double unsigned roundtrip", i);
    check((S)ds == s, "double signed roundtrip", i);
    check((U)lu == u, "long double unsigned roundtrip", i);
    check((S)ls == s, "long double signed roundtrip", i);
  }
  printf("C runtime: %d checks, %d failures\n", checks, failures);
  return failures != 0;
}
