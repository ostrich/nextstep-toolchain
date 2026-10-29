#import "objc-bridge.h"
#include <stdio.h>
#include <string.h>
#if defined(__hppa__)
#define ADD_ENCODING "i16@-4:-8i-12i-16"
/* NS3.3 HPPA returns encoded frame offsets, including self's -4. */
#define FIRST_ARGUMENT_OFFSET -4
#define LAST_ARGUMENT_OFFSET -16
#elif defined(__sparc__)
#define ADD_ENCODING "i16@0:4i8i12"
#define FIRST_ARGUMENT_OFFSET 0
#define LAST_ARGUMENT_OFFSET 12
#else
#define ADD_ENCODING "i16@8:12i16i20"
#define FIRST_ARGUMENT_OFFSET 0
#define LAST_ARGUMENT_OFFSET 12
#endif
static int checks, failures;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; printf("FAIL line %d: %s\n", __LINE__, #e); } } while (0)
@interface ModernProbe (Extra)
- (int)extra;
@end
@implementation ModernProbe (Extra)
- (int)extra { return stored + 100; }
@end
@interface BridgeForwarder : Object { id delegate; }
- initWithDelegate:object;
@end
@implementation BridgeForwarder
- initWithDelegate:object { self = [super init]; delegate = object; return self; }
- forward:(SEL)selector :(marg_list)frame { return [delegate performv:selector :frame]; }
@end
int main(void)
{
  id objects[4];
  int base[4] = { 11, 7, 20, 30 };
  int values[4] = { 11, 7, 22, 31 };
  int i, offset;
  const char *type;
  struct BridgePair p;
  struct BridgeTriple t;
  Method method;
  int (*implementation)(id, SEL);
  id<BridgeValues> forwarded;
  objects[0] = [[NativeProbe alloc] initWithValue:base[0]];
  objects[1] = [[ModernProbe alloc] initWithValue:base[1]];
  objects[2] = [[NativeChild alloc] initWithValue:base[2]];
  objects[3] = [[ModernChild alloc] initWithValue:base[3]];
  for (i = 0; i < 4; ++i) {
    CHECK([objects[i] value] == values[i]);
    CHECK([objects[i] respondsTo:@selector(value)]);
    p = [objects[i] pair:5]; CHECK(p.a == base[i] && p.b == 5);
    t = [objects[i] triple:9]; CHECK(t.a == base[i] && t.b == 9 && t.c == base[i] + 9);
    CHECK([objects[i] scale:1.25] == base[i] + 2.5);
    implementation = (int (*)(id, SEL))[objects[i] methodFor:@selector(value)];
    CHECK(implementation(objects[i], @selector(value)) == values[i]);
    CHECK([objects[i] conformsTo:@protocol(BridgeValues)]);
    method = class_getInstanceMethod((Class)[objects[i] class], @selector(add:to:));
    CHECK(method != 0 && !strcmp(method->method_types, ADD_ENCODING));
    CHECK(method_getNumberOfArguments(method) == 4);
    CHECK(method_getSizeOfArguments(method) == 16);
    method_getArgumentInfo(method, 0, &type, &offset);
    CHECK(type[0] == '@' && offset == FIRST_ARGUMENT_OFFSET);
    method_getArgumentInfo(method, 3, &type, &offset);
    CHECK(type[0] == 'i' && offset == LAST_ARGUMENT_OFFSET);
  }
  CHECK([(id<BridgeValues>)nil value] == 0);
  CHECK([objects[1] extra] == 107);
  forwarded = (id<BridgeValues>)[[BridgeForwarder alloc] initWithDelegate:objects[1]];
  CHECK([forwarded value] == 7);
  CHECK([forwarded add:2 to:3] == 12);
  [(id)forwarded free];
  for (i = 0; i < 4; ++i) [objects[i] free];
  printf("objc runtime: %d checks, %d failures\n", checks, failures);
  return failures != 0;
}
