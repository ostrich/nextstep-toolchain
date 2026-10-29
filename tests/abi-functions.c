#include "abi.h"
#include <stdarg.h>
#ifndef PREFIX
#error PREFIX must distinguish the native and modern objects
#endif
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(n) CAT(PREFIX,n)
static volatile int local_data[9];
volatile int FN(global_data)[3];
static const char text[] = "NeXT ABI";
int FN(integer)(int a, int b) { return a * 7 - b * 3; }
double FN(floating)(double d, float f, int n) { return d + f * n; }
struct pair FN(pair)(struct pair p, int n) { p.a += n; p.b -= n; return p; }
struct triple FN(triple)(struct triple p, int n) { p.a += n; p.b -= n; p.c *= n; return p; }
struct tiny FN(tiny)(struct tiny p) { p.a += 3; return p; }
struct wide FN(wide)(struct wide p) { p.d *= 2.0; p.n += 7; return p; }
long long FN(arithmetic)(long long a, long long b, unsigned n)
{ return ((a * b) >> n) + a / b + a % b; }
int FN(callback)(int (*f)(int, int), int a, int b) { return f(a, b) + 1; }
double FN(varargs)(int count, ...)
{
  va_list ap;
  double sum = 0;
  int i;
  va_start(ap, count);
  for (i = 0; i < count; ++i) {
    sum += va_arg(ap, int);
    sum += va_arg(ap, double);
  }
  va_end(ap);
  return sum;
}
int FN(data)(int n) { local_data[n & 7] = n; FN(global_data)[1] = n * 2; return local_data[n & 7] + text[n & 7] + FN(global_data)[1]; }
int FN(choose)(int n)
{
  switch (n) {
    case 0: return 93;
    case 1: return 17;
    case 2: return 52;
    case 3: return 8;
    case 4: return 74;
    case 5: return 31;
    default: return -9;
  }
}

int FN(aggregate_callback)(struct triple (*f)(struct triple, int),
                           struct pair (*g)(struct pair, int))
{
  struct triple t = { 8, 19, 3 };
  struct pair p = { 11, 27 };
  t = f(t, 5);
  p = g(p, 4);
  return t.a + t.b + t.c + p.a + p.b;
}

struct triple FN(aggregate_chain)(struct triple (*f)(struct triple, int),
                                  struct triple t, int n)
{
  t = f(t, n);
  t.c += 5;
  return t;
}
