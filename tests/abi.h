#ifndef NEXT_ABI_TEST_H
#define NEXT_ABI_TEST_H
struct pair { int a, b; };
struct triple { int a, b, c; };
struct tiny { unsigned char a; };
struct wide { double d; int n; };
#define DECLARE(P) \
  int P##integer(int, int); \
  double P##floating(double, float, int); \
  struct pair P##pair(struct pair, int); \
  struct triple P##triple(struct triple, int); \
  struct tiny P##tiny(struct tiny); \
  struct wide P##wide(struct wide); \
  long long P##arithmetic(long long, long long, unsigned); \
  int P##callback(int (*)(int, int), int, int); \
  double P##varargs(int, ...); \
  int P##data(int); \
  int P##choose(int); \
  int P##aggregate_callback(struct triple (*)(struct triple, int), struct pair (*)(struct pair, int)); \
  struct triple P##aggregate_chain(struct triple (*)(struct triple, int), struct triple, int);
DECLARE(native_)
DECLARE(modern_)
#endif
