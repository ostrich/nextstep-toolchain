/* Generated deterministic immediate-operand regression. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <math.h>
#include <string.h>
__attribute__((noipa)) static float return_one(void) { return 1.0f; }
__attribute__((noipa)) static float f0(float x) { return x + 0x0.0p+0f; }
__attribute__((noipa)) static float f1(float x) { return x + 0x1.0000000000000p+0f; }
__attribute__((noipa)) static float f2(float x) { return x + -0x1.8000000000000p+0f; }
__attribute__((noipa)) static float f3(float x) { return x + 0x1.0000000000000p-3f; }
__attribute__((noipa)) static float f4(float x) { return x + -0x1.0b299a0000000p-3f; }
__attribute__((noipa)) static float f5(float x) { return x + 0x1.6243ee0000000p-81f; }
__attribute__((noipa)) static float f6(float x) { return x + 0x1.3a5d780000000p+32f; }
__attribute__((noipa)) static float f7(float x) { return x + 0x1.474e440000000p+42f; }
__attribute__((noipa)) static float f8(float x) { return x + -0x1.cfa45e0000000p-19f; }
__attribute__((noipa)) static float f9(float x) { return x + -0x1.e7fb2c0000000p-87f; }
__attribute__((noipa)) static float f10(float x) { return x + 0x1.074c240000000p+73f; }
__attribute__((noipa)) static float f11(float x) { return x + -0x1.6e99fe0000000p+6f; }
__attribute__((noipa)) static float f12(float x) { return x + 0x1.2f53120000000p+80f; }
__attribute__((noipa)) static float f13(float x) { return x + 0x1.9cb5e80000000p+38f; }
__attribute__((noipa)) static float f14(float x) { return x + 0x1.c497fe0000000p-89f; }
__attribute__((noipa)) static float f15(float x) { return x + 0x1.d5543c0000000p+22f; }
__attribute__((noipa)) static float f16(float x) { return x + 0x1.aef50a0000000p-30f; }
__attribute__((noipa)) static float f17(float x) { return x + -0x1.a761fa0000000p+120f; }
__attribute__((noipa)) static float f18(float x) { return x + 0x1.54a9880000000p-103f; }
__attribute__((noipa)) static float f19(float x) { return x + -0x1.2f28bc0000000p-114f; }
__attribute__((noipa)) static float f20(float x) { return x + -0x1.9d4c2c0000000p+118f; }
__attribute__((noipa)) static float f21(float x) { return x + -0x1.d7ee460000000p+68f; }
__attribute__((noipa)) static float f22(float x) { return x + -0x1.5f9d680000000p-59f; }
__attribute__((noipa)) static float f23(float x) { return x + 0x1.5a30260000000p+58f; }
__attribute__((noipa)) static float f24(float x) { return x + 0x1.6bf8d60000000p+101f; }
__attribute__((noipa)) static float f25(float x) { return x + 0x1.39b0600000000p+74f; }
__attribute__((noipa)) static float f26(float x) { return x + -0x1.08d61a0000000p-99f; }
__attribute__((noipa)) static float f27(float x) { return x + -0x1.78b61e0000000p+34f; }
__attribute__((noipa)) static float f28(float x) { return x + -0x1.e877ae0000000p-112f; }
__attribute__((noipa)) static float f29(float x) { return x + -0x1.860bd00000000p-6f; }
__attribute__((noipa)) static float f30(float x) { return x + 0x1.6fb7cc0000000p-42f; }
__attribute__((noipa)) static float f31(float x) { return x + -0x1.d9f0940000000p+44f; }
static float (*const ffuncs[])(float) = {f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31};
static const float fexpected[] = {0x0.0p+0f,0x1.0000000000000p+0f,-0x1.8000000000000p+0f,0x1.0000000000000p-3f,-0x1.0b299a0000000p-3f,0x1.6243ee0000000p-81f,0x1.3a5d780000000p+32f,0x1.474e440000000p+42f,-0x1.cfa45e0000000p-19f,-0x1.e7fb2c0000000p-87f,0x1.074c240000000p+73f,-0x1.6e99fe0000000p+6f,0x1.2f53120000000p+80f,0x1.9cb5e80000000p+38f,0x1.c497fe0000000p-89f,0x1.d5543c0000000p+22f,0x1.aef50a0000000p-30f,-0x1.a761fa0000000p+120f,0x1.54a9880000000p-103f,-0x1.2f28bc0000000p-114f,-0x1.9d4c2c0000000p+118f,-0x1.d7ee460000000p+68f,-0x1.5f9d680000000p-59f,0x1.5a30260000000p+58f,0x1.6bf8d60000000p+101f,0x1.39b0600000000p+74f,-0x1.08d61a0000000p-99f,-0x1.78b61e0000000p+34f,-0x1.e877ae0000000p-112f,-0x1.860bd00000000p-6f,0x1.6fb7cc0000000p-42f,-0x1.d9f0940000000p+44f};
__attribute__((noipa)) static double d0(double x) { return x + 0x0.0p+0; }
__attribute__((noipa)) static double d1(double x) { return x + 0x1.0000000000000p+0; }
__attribute__((noipa)) static double d2(double x) { return x + -0x1.8000000000000p+0; }
__attribute__((noipa)) static double d3(double x) { return x + 0x1.0000000000000p-3; }
__attribute__((noipa)) static double d4(double x) { return x + 0x1.1933dfe931b7ep+463; }
__attribute__((noipa)) static double d5(double x) { return x + -0x1.6c7de7c3d037cp-717; }
__attribute__((noipa)) static double d6(double x) { return x + 0x1.4deda8f646c84p-737; }
__attribute__((noipa)) static double d7(double x) { return x + -0x1.b63926a492abep-78; }
__attribute__((noipa)) static double d8(double x) { return x + -0x1.7cc56d8f33ba2p-440; }
__attribute__((noipa)) static double d9(double x) { return x + -0x1.43540956b5776p+537; }
__attribute__((noipa)) static double d10(double x) { return x + 0x1.c55ef8a1871bcp-23; }
__attribute__((noipa)) static double d11(double x) { return x + 0x1.d7b22a73e2c9ep-418; }
__attribute__((noipa)) static double d12(double x) { return x + -0x1.e67e769441680p-717; }
__attribute__((noipa)) static double d13(double x) { return x + 0x1.7afb4ff966d50p-472; }
__attribute__((noipa)) static double d14(double x) { return x + -0x1.8b454568f6400p-280; }
__attribute__((noipa)) static double d15(double x) { return x + -0x1.4c2a807228b98p+162; }
__attribute__((noipa)) static double d16(double x) { return x + -0x1.017005b25abe8p+907; }
__attribute__((noipa)) static double d17(double x) { return x + 0x1.8674052722be8p+158; }
__attribute__((noipa)) static double d18(double x) { return x + 0x1.9d56adc2ab0fep-877; }
__attribute__((noipa)) static double d19(double x) { return x + -0x1.923af371a6e3ep-607; }
__attribute__((noipa)) static double d20(double x) { return x + 0x1.8d8ed7f6d67e6p+250; }
__attribute__((noipa)) static double d21(double x) { return x + 0x1.8da17b9b43b88p+349; }
__attribute__((noipa)) static double d22(double x) { return x + 0x1.b3e3114ce5124p-538; }
__attribute__((noipa)) static double d23(double x) { return x + 0x1.b0b0c42e39034p+783; }
__attribute__((noipa)) static double d24(double x) { return x + 0x1.66623fa0ec6b2p-385; }
__attribute__((noipa)) static double d25(double x) { return x + -0x1.08a76602b26b8p+353; }
__attribute__((noipa)) static double d26(double x) { return x + 0x1.8de3ba9e7cc7ap+18; }
__attribute__((noipa)) static double d27(double x) { return x + 0x1.8838702e2ec6cp-397; }
__attribute__((noipa)) static double d28(double x) { return x + 0x1.e5e69d4b027b2p-585; }
__attribute__((noipa)) static double d29(double x) { return x + -0x1.33d47b1a10fe0p-507; }
__attribute__((noipa)) static double d30(double x) { return x + 0x1.b8b2c31eca2dcp-139; }
__attribute__((noipa)) static double d31(double x) { return x + 0x1.eccb395e83a5cp-953; }
static double (*const dfuncs[])(double) = {d0,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31};
static const double dexpected[] = {0x0.0p+0,0x1.0000000000000p+0,-0x1.8000000000000p+0,0x1.0000000000000p-3,0x1.1933dfe931b7ep+463,-0x1.6c7de7c3d037cp-717,0x1.4deda8f646c84p-737,-0x1.b63926a492abep-78,-0x1.7cc56d8f33ba2p-440,-0x1.43540956b5776p+537,0x1.c55ef8a1871bcp-23,0x1.d7b22a73e2c9ep-418,-0x1.e67e769441680p-717,0x1.7afb4ff966d50p-472,-0x1.8b454568f6400p-280,-0x1.4c2a807228b98p+162,-0x1.017005b25abe8p+907,0x1.8674052722be8p+158,0x1.9d56adc2ab0fep-877,-0x1.923af371a6e3ep-607,0x1.8d8ed7f6d67e6p+250,0x1.8da17b9b43b88p+349,0x1.b3e3114ce5124p-538,0x1.b0b0c42e39034p+783,0x1.66623fa0ec6b2p-385,-0x1.08a76602b26b8p+353,0x1.8de3ba9e7cc7ap+18,0x1.8838702e2ec6cp-397,0x1.e5e69d4b027b2p-585,-0x1.33d47b1a10fe0p-507,0x1.b8b2c31eca2dcp-139,0x1.eccb395e83a5cp-953};
int main(void) {
 unsigned raw;
 volatile float stored = -1.5f;
 float returned = return_one();
 unsigned i, failures=0, checks=0; volatile float f=0; volatile double d=0;
 for(i=0;i<sizeof(ffuncs)/sizeof(ffuncs[0]);++i) { ++checks; if(ffuncs[i](f)!=fexpected[i]) { ++failures; printf("FAIL single %u\n",i); } }
 for(i=0;i<sizeof(dfuncs)/sizeof(dfuncs[0]);++i) { ++checks; if(dfuncs[i](d)!=dexpected[i]) { ++failures; printf("FAIL double %u\n",i); } }
 memcpy(&raw, (const void *)&stored, sizeof(raw)); ++checks;
 if (raw != 0xbfc00000U) { ++failures; printf("FAIL raw single store\n"); }
 memcpy(&raw, &returned, sizeof(raw)); ++checks;
 if (raw != 0x3f800000U) { ++failures; printf("FAIL raw single return\n"); }
 printf("floating immediates: %u checks, %u failures\n",checks,failures); return failures!=0;
}
