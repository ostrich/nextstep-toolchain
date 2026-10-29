#include <math.h>
#include <limits.h>
#include <string.h>
#include <signal.h>
#include <stdio.h>
#include <time.h>
#include <errno.h>
static unsigned checks,failures;
#define CHECK(x) do {++checks;if(!(x)){++failures;printf("FAIL %u: %s\n",checks,#x);}}while(0)
int main(void)
{
 char buffer[32], haystack[]="AbCdEf";struct tm utc,local,other;time_t epoch=0,stamp=1790000000;struct tm *native;
 CHECK(stpcpy(buffer,"abc")==buffer+3 && !strcmp(buffer,"abc"));
 CHECK(stpcpy(buffer,"")==buffer && !buffer[0]);
 CHECK(strcasestr(haystack,"cDe")==haystack+2);
 CHECK(strcasestr("abc","")!=0 && strcasestr("abc","abcd")==0);
 CHECK(strsignal(SIGTERM)!=0 && *strsignal(SIGTERM));
 CHECK(!strcmp(strsignal(-1),"Unknown signal"));
 CHECK(floorf(1.75f)==1.0f && floorf(-1.25f)==-2.0f);
 CHECK(signbit(floorf(-0.0f)) && isinf(floorf(INFINITY)) && isnan(floorf(NAN)));
 CHECK(round(0.5)==1 && round(-0.5)==-1 && round(1.5)==2 && round(-1.5)==-2);
 CHECK(round(0.499)==0 && signbit(round(-0.499)) && signbit(round(-0.0)));
 CHECK(isinf(round(INFINITY)) && isnan(round(NAN)));
 CHECK(round(4503599627370496.0)==4503599627370496.0);
 CHECK(lround(2.5)==3 && lround(-2.5)==-3 && lround(2.49)==2);
 CHECK(lround((double)LONG_MAX)==LONG_MAX && lround((double)LONG_MIN)==LONG_MIN);
 errno=0;CHECK(lround(INFINITY)==LONG_MIN && errno==EDOM);
 errno=0;CHECK(lround((double)LONG_MAX+1)==LONG_MIN && errno==EDOM);
 CHECK(gmtime_r(&epoch,&utc)==&utc && utc.tm_year==70 && utc.tm_mon==0 && utc.tm_mday==1);
 CHECK(gmtime_r(&stamp,&other)==&other && utc.tm_year==70);
 native=localtime(&stamp);CHECK(native!=0);if(native){struct tm saved=*native;CHECK(localtime_r(&stamp,&local)==&local && !memcmp(&saved,&local,sizeof(local)));}
 errno=0;CHECK(localtime_r(0,&local)==0 && errno==EINVAL);
 printf("PORT-INTERFACES %u checks %u failures\n",checks,failures);return failures!=0;
}
