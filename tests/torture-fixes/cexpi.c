/* Explicit builtin fallback must pass an addressable complex argument. */
#include <stdlib.h>
double _Complex cexp(double _Complex x) {
 if (__real__ x != 0 || __imag__ x != 2) abort();
 return 3 + 4i;
}
int main(void) {
 volatile double x = 2;
 double _Complex z = __builtin_cexpi(x);
 if (__real__ z != 3 || __imag__ z != 4) abort();
 return 0;
}
