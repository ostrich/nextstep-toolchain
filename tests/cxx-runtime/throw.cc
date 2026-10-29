/* SPDX-License-Identifier: 0BSD */
#include "fixture.h"
#include <stdlib.h>
#include <typeinfo>

int *zero_shared_address() { return &zero_shared; }
int *shared_value_address() { return &shared_value; }
const void *exception_type_address() { return &typeid(Value); }

void throw_value(int value)
{
  Guard guard(1);
  throw Value(value);
}

void rethrow_value(int value)
{
  Guard guard(2);
  try { throw_value(value); }
  catch (const Value &) { throw; }
}

static int compare(const void *, const void *)
{
  Guard guard(4);
  throw Value(73);
}

void throw_through_libc()
{
  int values[] = {3, 2, 1};
  Guard guard(8);
  qsort(values, 3, sizeof(int), compare);
}
