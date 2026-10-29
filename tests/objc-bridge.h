#ifndef NEXT_OBJC_BRIDGE_H
#define NEXT_OBJC_BRIDGE_H
#import <objc/Object.h>
struct BridgePair { int a, b; };
struct BridgeTriple { int a, b, c; };
@protocol BridgeValues
- initWithValue:(int)n;
- (int)value;
- (int)add:(int)a to:(int)b;
- (double)scale:(double)d;
- (struct BridgePair)pair:(int)n;
- (struct BridgeTriple)triple:(int)n;
@end
@interface NativeProbe : Object <BridgeValues> { int stored; }
@end
@interface ModernProbe : Object <BridgeValues> { int stored; }
@end
@interface NativeChild : ModernProbe
@end
@interface ModernChild : NativeProbe
@end
#endif
