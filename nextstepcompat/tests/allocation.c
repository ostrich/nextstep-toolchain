/* Allocating formatting must retain the bounded formatter's varargs ABI.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <errno.h>
static unsigned checks,failures;
static void check(int ok,const char *name){checks++;if(!ok){failures++;printf("FAIL %s\n",name);}}
static int allocate(char **out,const char *format,...)
{
    int n;va_list ap;va_start(ap,format);n=vasprintf(out,format,ap);va_end(ap);return n;
}
static void result(int n,char *s,const char *expected,const char *name)
{
    check(n==(int)strlen(expected),name);
    check(n>=0&&s&&!memcmp(s,expected,strlen(expected)+1),name);
    if(n>=0)free(s);
}
int main(void)
{
    char *s=NULL;int n,count=-1;unsigned i;
    n=asprintf(&s,"%s","hello");result(n,s,"hello","string allocation");
    n=asprintf(&s,"%s","");result(n,s,"","empty allocation");
    n=asprintf(&s,"%lld %llu",-9223372036854775807LL-1,18446744073709551615ULL);result(n,s,"-9223372036854775808 18446744073709551615","integer allocation");
    n=asprintf(&s,"%.2Lf %.2Le %.3Lg",4.2L,1.25L,4.2L);result(n,s,"4.20 1.25e+00 4.2","long double allocation");
    n=allocate(&s,"<%*.*Lf><%s>",8,2,1.25L,"done");result(n,s,"<    1.25><done>","va_list and star widths");
    n=asprintf(&s,"%.0Lf %.0Lf",2.5L,3.5L);result(n,s,"2 4","rounding allocation");
    n=asprintf(&s,"%.1Lf",-0.0L);result(n,s,"-0.0","negative zero");
    n=asprintf(&s,"%ls",L"ABC");result(n,s,"ABC","single-byte wide string");
    n=asprintf(&s,"abc%nxyz",&count);check(count==3,"count conversion");result(n,s,"abcxyz","count allocation");
    n=asprintf(&s,"%c",0);check(n==1&&s&&s[0]==0&&s[1]==0,"embedded nul allocation");if(n>=0)free(s);
    for(i=0;i<100;i++){n=allocate(&s,"%u:%.2Lf",i,1.25L);check(n>=6&&s&&strstr(s,":1.25"),"allocation reuse");if(n>=0)free(s);}
    s=NULL;errno=0;n=allocate(&s,"%");check(n<0&&errno==EINVAL,"invalid format rejected");
    printf("ALLOCATING FORMAT: %u checks, %u failures\n",checks,failures);return failures!=0;
}
