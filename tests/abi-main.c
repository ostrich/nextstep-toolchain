#include "abi.h"
extern int printf(const char *, ...);
static int failures;
static int checks;
#define CHECK(expr) do { ++checks; if (!(expr)) { printf("FAIL line %d: %s\n", __LINE__, #expr); ++failures; } } while (0)
#define TEST(P) do { \
  struct pair p = { 11, 27 }; \
  struct triple t = { 8, 19, 3 }; \
  struct tiny c = { 250 }; \
  struct wide w = { 1.25, 9 }; \
  p = P##pair(p, 4); \
  CHECK(p.a == 15 && p.b == 23); \
  t = P##triple(t, 5); \
  CHECK(t.a == 13 && t.b == 14 && t.c == 15); \
  c = P##tiny(c); CHECK(c.a == 253); \
  w = P##wide(w); CHECK(w.d == 2.5 && w.n == 16); \
  CHECK(P##integer(-17, 6) == -137); \
  CHECK(P##floating(1.25, 2.5f, 3) == 8.75); \
  CHECK(P##varargs(3, 2, 1.5, -3, 2.25, 4, -0.5) == 6.25); \
  CHECK(P##arithmetic(-1234567890123LL, 17, 4) == -1384350023859LL); \
  CHECK(P##arithmetic(-1, 17, 4) == -3); \
  CHECK(P##arithmetic(-1234, -17, 0) == 21040); \
  CHECK(P##arithmetic(4294967299LL, 7, 33) == 613566760LL); \
  CHECK(P##data(3) == 93); \
  CHECK(P##choose(3) == 8 && P##choose(99) == -9); \
} while (0)
int main(void)
{
  struct triple t = { 8, 19, 3 };
  struct triple r;
  TEST(native_);
  TEST(modern_);
  CHECK(native_callback(modern_integer, 3, 5) == 7);
  CHECK(modern_callback(native_integer, 3, 5) == 7);
  CHECK(native_aggregate_callback(modern_triple, modern_pair) == 80);
  CHECK(modern_aggregate_callback(native_triple, native_pair) == 80);
  r = native_aggregate_chain(modern_triple, t, 5);
  CHECK(r.a == 13 && r.b == 14 && r.c == 20);
  r = modern_aggregate_chain(native_triple, t, 5);
  CHECK(r.a == 13 && r.b == 14 && r.c == 20);
  printf("mixed ABI: %d checks, %d failures\n", checks, failures);
  return failures != 0;
}
