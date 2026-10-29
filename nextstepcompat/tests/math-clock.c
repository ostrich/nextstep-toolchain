/* Binary64 edge cases and realtime-only clock contract.
   SPDX-License-Identifier: 0BSD */
#include <math.h>
#include <time.h>
#include <sys/time.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#ifdef NS33_HOST_TEST
extern double ns33_fmin(double, double), ns33_fmax(double, double), ns33_log2(double);
extern int ns33_clock_gettime(clockid_t, struct timespec *);
#undef fmin
#undef fmax
#undef log2
#undef clock_gettime
#define fmin ns33_fmin
#define fmax ns33_fmax
#define log2 ns33_log2
#define clock_gettime ns33_clock_gettime
#endif
#include "math-log2-vectors.h"
static unsigned failures, checks;
#define CHECK(x) do { checks++; if (!(x)) { failures++; \
  printf("FAIL line %d: %s\n", __LINE__, #x); } } while (0)
static uint64_t bits(double x)
{
  union { double d; uint64_t u; } v;
  v.d = x;
  return v.u;
}
int main(void)
{
  volatile double negative_zero = -0.0, zero = 0.0, nan = NAN, inf = INFINITY;
  double (*volatile minimum)(double, double) = fmin;
  double (*volatile maximum)(double, double) = fmax;
  double (*volatile logarithm)(double) = log2;
  unsigned i;
  int exponent;
  struct timeval before, after;
  struct timespec stamp;
  CHECK(signbit(minimum(zero, negative_zero)));
  CHECK(signbit(minimum(negative_zero, zero)));
  CHECK(!signbit(maximum(zero, negative_zero)));
  CHECK(!signbit(maximum(negative_zero, zero)));
  CHECK(minimum(nan, 2) == 2 && minimum(2, nan) == 2);
  CHECK(maximum(nan, 2) == 2 && maximum(2, nan) == 2);
  CHECK(isnan(minimum(nan, nan)) && isnan(maximum(nan, nan)));
  CHECK(minimum(-inf, inf) == -inf && maximum(-inf, inf) == inf);
  CHECK(minimum(-3, 2) == -3 && maximum(-3, 2) == 2);
  CHECK(minimum(3, 2) == 2 && maximum(3, 2) == 3);
  errno = 0;
  CHECK(logarithm(zero) == -inf && errno == ERANGE);
  errno = 0;
  CHECK(logarithm(negative_zero) == -inf && errno == ERANGE);
  errno = 0;
  CHECK(isnan(logarithm(-1)) && errno == EDOM);
  errno = 0;
  CHECK(isnan(logarithm(-inf)) && errno == EDOM);
  CHECK(logarithm(inf) == inf);
  CHECK(isnan(logarithm(nan)));
  CHECK(bits(logarithm(1)) == bits(0.0));
  for (exponent = -1074; exponent <= 1023; exponent++) {
    union { uint64_t u; double d; } power;
    double actual;
    /* Do not make the log2 test depend on the native ldexp's underflow
       behavior. Construct exact normal and subnormal powers directly. */
    power.u = exponent >= -1022 ? (uint64_t)(exponent + 1023) << 52 :
        (uint64_t)1 << (exponent + 1074);
    actual = logarithm(power.d);
    if (actual != exponent)
      printf("log2 power exponent=%d input=%a actual=%a\n", exponent, power.d, actual);
    CHECK(actual == exponent);
  }
  for (i = 0; i < sizeof(log2_vectors) / sizeof(log2_vectors[0]); i++) {
    double x = logarithm(log2_vectors[i].x);
    uint64_t a = bits(x), b = bits(log2_vectors[i].expected);
    uint64_t distance = a > b ? a - b : b - a;
    CHECK(isfinite(x) && signbit(x) == signbit(log2_vectors[i].expected) && distance <= 1);
  }
  CHECK(gettimeofday(&before, 0) == 0);
  CHECK(clock_gettime(CLOCK_REALTIME, &stamp) == 0);
  CHECK(gettimeofday(&after, 0) == 0);
  CHECK(stamp.tv_nsec >= 0 && stamp.tv_nsec < 1000000000L);
  CHECK(stamp.tv_nsec % 1000 == 0);
  CHECK(stamp.tv_sec > before.tv_sec ||
        (stamp.tv_sec == before.tv_sec && stamp.tv_nsec >= before.tv_usec * 1000L));
  CHECK(stamp.tv_sec < after.tv_sec ||
        (stamp.tv_sec == after.tv_sec && stamp.tv_nsec <= after.tv_usec * 1000L));
  stamp.tv_sec = 123; stamp.tv_nsec = 456;
  errno = 0;
  CHECK(clock_gettime(CLOCK_MONOTONIC, &stamp) == -1 && errno == ENOTSUP);
  CHECK(stamp.tv_sec == 123 && stamp.tv_nsec == 456);
  errno = 0;
  CHECK(clock_gettime(-7, &stamp) == -1 && errno == EINVAL);
  CHECK(stamp.tv_sec == 123 && stamp.tv_nsec == 456);
  printf("%s math-clock: %u checks, %u failures\n", failures ? "FAIL" : "PASS", checks, failures);
  return failures != 0;
}
