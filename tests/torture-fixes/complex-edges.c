/* Annex G-style special values and scaling, using upstream libgcc helpers. */
#include <float.h>
#include <stdlib.h>
#define TEST(T, NAME, MAX) \
static void NAME(void) { \
 volatile T _Complex a, b; T _Complex z; \
 __real__ a = 1; __imag__ a = 2; \
 __real__ b = 0; __imag__ b = 0; z = a / b; \
 if (!__builtin_isinf(__real__ z) || !__builtin_isinf(__imag__ z)) abort(); \
 __real__ b = __builtin_inf(); __imag__ b = 0; z = a / b; \
 if (__real__ z != 0 || __imag__ z != 0) abort(); \
 __real__ a = __builtin_inf(); __imag__ a = 2; \
 __real__ b = 1; __imag__ b = 2; z = a / b; \
 if (!__builtin_isinf(__real__ z) || !__builtin_isinf(__imag__ z) || !(__imag__ z < 0)) abort(); \
 __real__ a = __builtin_nan(""); __imag__ a = __builtin_nan(""); z = a / b; \
 if (!__builtin_isnan(__real__ z) || !__builtin_isnan(__imag__ z)) abort(); \
 __real__ a = MAX / 4; __imag__ a = MAX / 4; b = a; z = a / b; \
 if (__real__ z != 1 || __imag__ z != 0) abort(); \
 __real__ a = __builtin_inf(); __imag__ a = 0; z = a * b; \
 if (!__builtin_isinf(__real__ z) || !__builtin_isinf(__imag__ z)) abort(); \
}
TEST(float, single, FLT_MAX)
TEST(double, dbl, DBL_MAX)
TEST(long double, extended, LDBL_MAX)
int main(void) { single(); dbl(); extended(); return 0; }
