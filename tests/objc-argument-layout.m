/* Header-free metadata fixture for comparison with the original compiler. */
struct Pair { int a, b; };
struct Triple { int a, b, c; };
@interface ArgumentProbe
- (int)mix:(int)a wide:(double)b narrow:(char)c;
- (int)floats:(float)a single:(float)b wide:(double)c;
- (int)large:(struct Triple)a pair:(struct Pair)b integer:(int)c;
- (int)narrow:(char)a short:(short)b integer:(int)c;
- (int)stack:(int)a b:(int)b c:(int)c d:(int)d e:(int)e wide:(double)f;
@end
@implementation ArgumentProbe
- (int)mix:(int)a wide:(double)b narrow:(char)c { return a + (int)b + c; }
- (int)floats:(float)a single:(float)b wide:(double)c { return (int)(a+b+c); }
- (int)large:(struct Triple)a pair:(struct Pair)b integer:(int)c { return a.a+b.b+c; }
- (int)narrow:(char)a short:(short)b integer:(int)c { return a+b+c; }
- (int)stack:(int)a b:(int)b c:(int)c d:(int)d e:(int)e wide:(double)f { return a+b+c+d+e+(int)f; }
@end
