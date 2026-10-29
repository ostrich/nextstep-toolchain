#include <stdio.h>
static int constructed;
struct Value {
  int value;
  Value() : value(42) { constructed = 1; }
  ~Value() {
    constructed = 0;
    printf("cxx destructor: %d\n", value);
    fflush(stdout);
  }
};
static Value global;
int main() {
  printf("cxx probe: %d %d\n", constructed, global.value);
  return constructed != 1 || global.value != 42;
}
