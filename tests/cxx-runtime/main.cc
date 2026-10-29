/* SPDX-License-Identifier: 0BSD */
#include "fixture.h"
#include <exception>
#include <typeinfo>
#include <new>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <time.h>

int destroyed;
static volatile long double numerator = 1.0L;
static long double initialized_third = numerator / 3.0L;
static int checks, failures;
static void check(bool value, const char *name)
{
  ++checks;
  if (!value) { ++failures; printf("FAIL %s\n", name); }
}

struct Base { virtual ~Base() {} };
struct Left: virtual Base { int left; };
struct Right: virtual Base { int right; };
struct Derived: Left, Right {};
struct Other: Base {};

struct StaticValue {
  static int attempts;
  StaticValue() { if (++attempts == 1) throw Value(19); }
};
int StaticValue::attempts;
static StaticValue &local_static()
{
  static StaticValue value;
  return value;
}

int main()
{
#if __LDBL_MANT_DIG__ > __DBL_MANT_DIG__
  check(initialized_third > static_cast<long double>(1.0 / 3.0),
        "extended precision before user constructors");
#endif
  try { throw_value(42); check(false, "throw did not escape"); }
  catch (const Value &v) { check(v.number == 42, "cross-unit catch value"); }
  check(destroyed == 1, "destructor during unwind");
  try { rethrow_value(51); }
  catch (const Value &v) { check(v.number == 51, "cross-unit rethrow"); }
  check(destroyed == 4, "nested destructor cleanup");
  try { throw_through_libc(); }
  catch (const Value &v) { check(v.number == 73, "unwind across original libc"); }
  check(destroyed == 16, "libc callback destructor cleanup");
  for (int i = 0; i != 100; ++i) {
    try { throw_value(i); }
    catch (const Value &v) { check(v.number == i, "repeated exceptions"); }
  }
  check(zero_shared_address() == &zero_shared && zero_shared == 0, "coalesced zero initialized variable");
  check(shared_value_address() == &shared_value, "coalesced inline variable");
  check(exception_type_address() == &typeid(Value), "coalesced typeinfo");
  Derived object;
  Base *base = &object;
  check(dynamic_cast<Derived *>(base) == &object, "virtual-base downcast");
  check(dynamic_cast<Right *>(static_cast<Left *>(&object)) == static_cast<Right *>(&object), "crosscast");
  check(dynamic_cast<Other *>(base) == 0, "failed pointer cast");
  check(typeid(*base) == typeid(Derived), "dynamic typeid");
  try { (void)dynamic_cast<Other &>(*base); check(false, "bad_cast missing"); }
  catch (const std::bad_cast &) { check(true, "bad_cast"); }
  try { (void)local_static(); check(false, "static initializer exception missing"); }
  catch (const Value &v) { check(v.number == 19, "static initializer exception"); }
  StaticValue *first = &local_static();
  check(&local_static() == first && StaticValue::attempts == 2, "guard abort and retry");
  int *array = new int[128];
  array[127] = 79;
  check(array[127] == 79, "new array");
  delete[] array;
  check(strcoll("abc", "abd") < 0, "C locale collation");
  check(strxfrm(0, "abc", 0) == 3, "transform length query");
  char transformed[4];
  check(strxfrm(transformed, "abc", sizeof(transformed)) == 3
        && strcmp(transformed, "abc") == 0, "C locale transform");
  check(EILSEQ != EINVAL && ENOMSG != EAGAIN, "distinct runtime error codes");
  check(strstr(strerror(EILSEQ), "multibyte") != 0, "byte sequence error text");
  check(strstr(strerror(ENOMSG), "message") != 0, "message error text");
  check(strcmp(strerror(-1), "Unknown error") == 0, "negative error number");
  char message[128];
  errno = EDOM;
  check(strerror_r(EILSEQ, message, sizeof(message)) == 0
        && strstr(message, "multibyte") != 0, "bounded error text");
  check(errno == EDOM, "strerror_r preserves errno");
  char short_message[3] = {1, 1, 1};
  check(strerror_r(EILSEQ, short_message, sizeof(short_message)) == ERANGE
        && short_message[2] == 0, "error text truncation");
  check(strerror_r(EINVAL, 0, 0) == ERANGE, "zero size error buffer");
  check(strerror_r(-1, message, sizeof(message)) == EINVAL, "invalid error status");
  timespec timestamp = {42, 123};
  check(timestamp.tv_sec == 42 && timestamp.tv_nsec == 123, "POSIX time representation");
  std::exception_ptr saved;
  try { throw_value(81); }
  catch (...) { saved = std::current_exception(); }
  try { std::rethrow_exception(saved); }
  catch (const Value &v) { check(v.number == 81, "exception_ptr"); }
  printf("cxx-runtime: %d checks, %d failures\n", checks, failures);
  return failures != 0;
}
