/* Native/new SPARC NeXT aggregate return boundaries. */
struct byte_value { unsigned char x; };
struct half_value { unsigned short x; };
struct word_value { unsigned x; };
struct bytes3 { unsigned char x[3]; };
struct words2 { unsigned x, y; };
struct float_value { float x; };
struct double_value { double x; };
struct halves2 { unsigned short x, y; };
struct bytes2 { unsigned char x[2]; };
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define DECLARE(P) \
 struct byte_value CAT(P,byte_value)(struct byte_value); \
 struct half_value CAT(P,half_value)(struct half_value); \
 struct word_value CAT(P,word_value)(struct word_value); \
 struct bytes3 CAT(P,bytes3)(struct bytes3); \
 struct words2 CAT(P,words2)(struct words2); \
 struct float_value CAT(P,float_value)(struct float_value); \
 struct double_value CAT(P,double_value)(struct double_value); \
 struct halves2 CAT(P,halves2)(struct halves2); \
 struct bytes2 CAT(P,bytes2)(struct bytes2);
DECLARE(native_)
DECLARE(modern_)
#ifdef PREFIX
struct byte_value CAT(PREFIX,byte_value)(struct byte_value p) { p.x += 3; return p; }
struct half_value CAT(PREFIX,half_value)(struct half_value p) { p.x += 3; return p; }
struct word_value CAT(PREFIX,word_value)(struct word_value p) { p.x += 3; return p; }
struct bytes3 CAT(PREFIX,bytes3)(struct bytes3 p) { p.x[0]+=1; p.x[1]+=2; p.x[2]+=3; return p; }
struct words2 CAT(PREFIX,words2)(struct words2 p) { p.x+=3; p.y+=5; return p; }
struct float_value CAT(PREFIX,float_value)(struct float_value p) { p.x *= 2; return p; }
struct double_value CAT(PREFIX,double_value)(struct double_value p) { p.x *= 2; return p; }
struct halves2 CAT(PREFIX,halves2)(struct halves2 p) { p.x+=3; p.y+=5; return p; }
struct bytes2 CAT(PREFIX,bytes2)(struct bytes2 p) { p.x[0]+=3; p.x[1]+=5; return p; }
#else
extern int printf(const char *, ...);
static int checks, failures;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; printf("FAIL %d %s\n", __LINE__, #e); } } while (0)
#define TEST(P) do { \
 struct byte_value a={250}; struct half_value b={65000}; \
 struct word_value c={123456}; struct bytes3 d={{11,22,33}}; \
 struct words2 e={111,222}; struct float_value f={1.25f}; \
 struct double_value g={1.25}; struct halves2 h={111,222}; \
 struct bytes2 i={{111,222}}; \
 a=CAT(P,byte_value)(a); CHECK(a.x==253); \
 b=CAT(P,half_value)(b); CHECK(b.x==65003); \
 c=CAT(P,word_value)(c); CHECK(c.x==123459); \
 d=CAT(P,bytes3)(d); CHECK(d.x[0]==12 && d.x[1]==24 && d.x[2]==36); \
 e=CAT(P,words2)(e); CHECK(e.x==114 && e.y==227); \
 f=CAT(P,float_value)(f); CHECK(f.x==2.5f); \
 g=CAT(P,double_value)(g); CHECK(g.x==2.5); \
 h=CAT(P,halves2)(h); CHECK(h.x==114 && h.y==227); \
 i=CAT(P,bytes2)(i); CHECK(i.x[0]==114 && i.x[1]==227); \
} while (0)
int main(void)
{
 TEST(native_);
 TEST(modern_);
 printf("SPARC small aggregates: %d checks, %d failures\n",checks,failures);
 return failures != 0;
}
#endif
