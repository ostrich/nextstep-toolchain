/* Exercise runtime complex multiply/divide without constant folding. */
#include <stdlib.h>
#define CHECK(T, SUFFIX) do { \
 volatile T _Complex a = 3 + 4i, b = 1 + 2i; \
 T _Complex c = a / b, d = a * b; \
 T r = __real__ c, i = __imag__ c; \
 if (r < (T)2.199 || r > (T)2.201 || i < (T)-.401 || i > (T)-.399) abort(); \
 if (__real__ d != (T)-5 || __imag__ d != (T)10) abort(); \
} while (0)
int main(void) { CHECK(float, f); CHECK(double, d); CHECK(long double, l); return 0; }
