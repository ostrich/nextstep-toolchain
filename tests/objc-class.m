#import "objc-bridge.h"
#ifndef PROBE_CLASS
#error Select the class implemented by this compiler
#endif
@implementation PROBE_CLASS
- initWithValue:(int)n { self = [super init]; stored = n; return self; }
- (int)value { return stored; }
- (int)add:(int)a to:(int)b { return stored + a + b; }
- (double)scale:(double)d { return stored + d * 2.0; }
- (struct BridgePair)pair:(int)n
{ struct BridgePair p; p.a = stored; p.b = n; return p; }
- (struct BridgeTriple)triple:(int)n
{ struct BridgeTriple t; t.a = stored; t.b = n; t.c = stored + n; return t; }
@end
@implementation PROBE_CHILD
- (int)value { return [super value] + CHILD_DELTA; }
@end
