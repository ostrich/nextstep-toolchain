/* SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEP_CXX_EXCEPTION_FIXTURE_H
#define NEXTSTEP_CXX_EXCEPTION_FIXTURE_H
extern int destroyed;
struct Guard {
  int amount;
  explicit Guard(int value): amount(value) {}
  ~Guard() { destroyed += amount; }
};
struct Value { int number; explicit Value(int value): number(value) {} };
inline int shared_value = 37;
inline int zero_shared;
int *zero_shared_address();
int *shared_value_address();
const void *exception_type_address();
void throw_value(int);
void rethrow_value(int);
void throw_through_libc();
#endif
