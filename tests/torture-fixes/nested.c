#include <stdlib.h>
static int invoke(int (*f)(int), int n) { return f(n); }
static int outer(int a) {
 int x = a + 3;
 int middle(int b) {
  int y = b + 5;
  int inner(int c) { return x + y + c; }
  return invoke(inner, 11);
 }
 return invoke(middle, 7);
}
int main(void) { if (outer(2) != 28 || outer(10) != 36) abort(); return 0; }
