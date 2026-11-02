/* Exercise incoming hidden arguments across large-frame prologues.
   Keep direct-only functions separate from address-taken functions: GCC may
   use a local register-argument convention only for the former. */
#include <stdio.h>
#include <string.h>

#define KEEP __attribute__((noinline, noclone))
#define ARGS unsigned a, unsigned b, unsigned c, unsigned d, unsigned e, unsigned f, unsigned g, unsigned h
#define PASS a,b,c,d,e,f,g,h
#define VALUES seed,seed+1,seed+2,seed+3,seed+4,seed+5,seed+6,seed+7
#define SUM (a+3*b+5*c+7*d+11*e+13*f+17*g+19*h)
static unsigned failures, checks;

static unsigned char byte(unsigned seed, unsigned i)
{
    return (unsigned char)((seed + 13*i) ^ (i >> 3));
}

static void check(const unsigned char *p, unsigned size, unsigned seed,
                  const char *name, const char *mode)
{
    unsigned i;
    ++checks;
    for (i=0; i<size; ++i)
        if (p[i] != byte(seed,i)) {
            printf("FAIL %s %s byte %u expected %u got %u\n",
                   name,mode,i,byte(seed,i),p[i]);
            ++failures;
            return;
        }
}

/* Volatile writes and reads retain the frame and all eight input values.
   Check page-spaced contents as well as the final byte. */
#define FRAME(N) \
    volatile unsigned char frame[N]; unsigned i, mix=SUM; \
    for (i=0; i<N; i+=4096) frame[i]=byte(mix,i); \
    frame[N-1]=byte(mix,N-1); \
    __asm__ volatile ("" : : "m"(frame) : "memory"); \
    for (i=0; i<N; i+=4096) if (frame[i]!=byte(mix,i)) ++failures; \
    if (frame[N-1]!=byte(mix,N-1)) ++failures;

#define CASE(S,N) \
struct result_##S##_##N { unsigned char bytes[S]; }; \
static KEEP struct result_##S##_##N direct_##S##_##N(ARGS) { \
    struct result_##S##_##N r; FRAME(N) \
    for(i=0;i<S;++i) r.bytes[i]=byte(mix,i); return r; \
} \
static KEEP struct result_##S##_##N indirect_##S##_##N(ARGS) { \
    struct result_##S##_##N r; FRAME(N) \
    for(i=0;i<S;++i) r.bytes[i]=byte(mix,i); return r; \
} \
static KEEP void test_##S##_##N(unsigned seed) { \
    unsigned a=seed,b=seed+1,c=seed+2,d=seed+3,e=seed+4,f=seed+5,g=seed+6,h=seed+7; \
    unsigned expected=SUM; volatile unsigned bias=seed*23+1; \
    struct result_##S##_##N r; \
    struct result_##S##_##N (*volatile fn)(ARGS)=indirect_##S##_##N; \
    KEEP struct result_##S##_##N nested(ARGS) { \
        struct result_##S##_##N r; FRAME(N) \
        for(i=0;i<S;++i) r.bytes[i]=byte(mix+bias,i); return r; \
    } \
    struct result_##S##_##N (*volatile nf)(ARGS)=nested; \
    r=direct_##S##_##N(VALUES); check(r.bytes,S,expected,#S "/" #N,"direct"); \
    r=fn(VALUES); check(r.bytes,S,expected,#S "/" #N,"indirect"); \
    r=nested(VALUES); check(r.bytes,S,expected+bias,#S "/" #N,"nested-direct"); \
    r=nf(VALUES); check(r.bytes,S,expected+bias,#S "/" #N,"nested-indirect"); \
}
#define SIZES(N) CASE(12,N) CASE(1460,N) CASE(8196,N)
SIZES(64)
SIZES(3584)
SIZES(4096)
SIZES(4608)
SIZES(12288)
SIZES(65536)

#define SCALAR(N) \
static KEEP unsigned scalar_##N(ARGS) { FRAME(N) return mix; }
SCALAR(64) SCALAR(3584) SCALAR(4096) SCALAR(4608) SCALAR(12288) SCALAR(65536)
#define RUN(N) \
    test_12_##N(seed); test_1460_##N(seed); test_8196_##N(seed); \
    ++checks; if(scalar_##N(VALUES)!=expected) { ++failures; printf("FAIL scalar " #N "\n"); }
int main(int argc, char **argv)
{
    unsigned round;
    if(argc==2 && !strcmp(argv[1],"--arch")) { puts(TEST_ARCH); return 0; }
    for(round=0;round<3;++round) {
        unsigned seed=argc+round*7;
        unsigned a=seed,b=seed+1,c=seed+2,d=seed+3,e=seed+4,f=seed+5,g=seed+6,h=seed+7;
        unsigned expected=SUM;
        RUN(64) RUN(3584) RUN(4096) RUN(4608) RUN(12288) RUN(65536)
    }
    printf("%s prologues: %u checks, %u failures\n",TEST_ARCH,checks,failures);
    return failures ? 1 : 0;
}
