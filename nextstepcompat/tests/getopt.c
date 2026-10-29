#include <getopt.h>
#include <stdio.h>
#include <string.h>
static int checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; printf("FAIL %d: %s\n", checks, #x); } } while (0)
static const struct option options[] = {
 {"alpha", no_argument, 0, 'a'}, {"alpine", no_argument, 0, 'p'},
 {"beta", required_argument, 0, 'b'}, {"color", optional_argument, 0, 'c'},
 {0,0,0,0}
};
static void reset(void) { optind = 0; opterr = 0; optarg = 0; optopt = 0; }
int main(void)
{
 int i = -1;
 char *a[] = {"test", "--alpha", "--beta=value", "--color=red", "file", 0};
 reset(); CHECK(getopt_long(5,a,"ab:c::",options,&i)=='a' && i==0);
 CHECK(getopt_long(5,a,"ab:c::",options,&i)=='b' && i==2 && strcmp(optarg,"value")==0);
 CHECK(getopt_long(5,a,"ab:c::",options,&i)=='c' && strcmp(optarg,"red")==0);
 CHECK(getopt_long(5,a,"ab:c::",options,&i)==-1 && optind==4);
 { char *v[]={"test","-ab","value",0}; reset(); CHECK(getopt_long(3,v,"ab:",options,0)=='a');
 CHECK(getopt_long(3,v,"ab:",options,0)=='b' && !strcmp(optarg,"value")); CHECK(getopt_long(3,v,"ab:",options,0)==-1); }
 { char *v[]={"test","--al",0}; reset(); CHECK(getopt_long(2,v,"",options,0)=='?'); }
 { char *v[]={"test","--beta",0}; reset(); CHECK(getopt_long(2,v,":b:",options,0)==':' && optopt=='b'); }
 { char *v[]={"test","--unknown",0}; reset(); CHECK(getopt_long(2,v,"",options,0)=='?'); }
 { char *v[]={"test","file","--alpha",0}; reset(); CHECK(getopt_long(3,v,"",options,0)=='a'); CHECK(optind==2 && !strcmp(v[1],"--alpha") && !strcmp(v[2],"file")); }
 { char *v[]={"test","file","--alpha",0}; reset(); CHECK(getopt_long(3,v,"+",options,0)==-1 && optind==1); }
 { char *v[]={"test","--color", "file",0}; reset(); CHECK(getopt_long(3,v,"",options,0)=='c' && optarg==0 && optind==2); }
 { char *v[]={"test","--", "--alpha",0}; reset(); CHECK(getopt_long(3,v,"",options,0)==-1 && optind==2); }
 { char *v[]={"test","--alpha=bad",0}; reset(); CHECK(getopt_long(2,v,"",options,0)=='?'); }
 { char *v[]={"test","-alpha",0}; reset(); CHECK(getopt_long_only(2,v,"",options,0)=='a'); }
 { char *v[]={"test","-a",0}; reset(); CHECK(getopt(2,v,"a")=='a'); optreset=1; CHECK(getopt(2,v,"a")=='a'); CHECK(getopt(2,v,"a")==-1); }
 { int flag=0; struct option opts[]={{"set",no_argument,&flag,7},{0,0,0,0}};char *v[]={"test","--set",0};reset();CHECK(getopt_long(2,v,"",opts,&i)==0 && flag==7 && i==0); }
 printf("GETOPT %d checks %d failures\n",checks,failures);return failures!=0;
}
