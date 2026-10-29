/* Type probe for the original 3.3 frontend and modern GCC. */
int size_check(__typeof__(sizeof(int)));
int size_check(unsigned long);
int difference_check(__typeof__((char *)0 - (char *)0));
#ifdef EXPECT_INT_PTRDIFF
int difference_check(int);
#else
int difference_check(long);
#endif
int wide_check(__typeof__(L"x"[0]));
int wide_check(unsigned short);
int wide_size = sizeof(L"x"[0]);
int wide_sign = ((__typeof__(L"x"[0])) -1) < 0;
int pointer_size = sizeof(void *);
int long_size = sizeof(long);
int long_double_size = sizeof(long double);
struct double_alignment { char c; double d; };
int aligned_double_size = sizeof(struct double_alignment);
