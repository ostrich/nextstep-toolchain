/* Check the declared POSIX group-array ABI against native BSD results.
   SPDX-License-Identifier: 0BSD */
#define _NEXT_SOURCE 1
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
extern int native_setgroups(int,const int *) __asm__("_setgroups");
extern int native_getgroups(int,int *) __asm__("_getgroups");
static unsigned checks,failures;
static void check(int yes,const char *name){checks++;if(!yes){failures++;printf("FAIL %s\n",name);}}
static int run(void)
{
    int want[]={1,0x1234,0x7000},native[16],n;unsigned i;
    struct {gid_t ids[4];unsigned char tail[16];} result;
    if(native_setgroups(0,NULL)){perror("empty group setup");return 2;}
    check(getgroups(0,NULL)==0,"empty group query");
    if(native_setgroups(3,want)||setgid(1)||setuid(1)){perror("test identity");return 2;}
    printf("GROUP ABI gid_t=%u native int=%u\n",(unsigned)sizeof(gid_t),(unsigned)sizeof(int));
    n=native_getgroups(16,native);check(n==3,"native count");
    if(n==3)for(i=0;i<3;i++){
        if(native[i]!=want[i])printf("native group %u got=%d expected=%d\n",i,native[i],want[i]);
        check(native[i]==want[i],"native values");
    }
    check(getgroups(0,NULL)==3,"POSIX count-only query");
    memset(&result,0xa5,sizeof(result));n=getgroups(4,result.ids);check(n==3,"POSIX result count");
    if(n==3)for(i=0;i<3;i++)check(result.ids[i]==(gid_t)want[i],"POSIX group values");
    check(result.ids[3]==(gid_t)0xa5a5,"unused group element unchanged");
    for(i=0;i<sizeof(result.tail);i++)check(result.tail[i]==0xa5,"group output stays in bounds");
    errno=0;check(getgroups(2,result.ids)==-1&&errno==EINVAL,"small array rejected");
    errno=0;check(getgroups(-1,result.ids)==-1&&errno==EINVAL,"negative size rejected");
    check(getgroups(3,result.ids)==3,"exact-size array");
    errno=0;check(getgroups(3,NULL)==-1&&errno==EFAULT,"null output rejected");
    printf("GROUPS: %u checks, %u failures\n",checks,failures);return failures!=0;
}
int main(void)
{
    pid_t p;int s=-1;setbuf(stdout,NULL);signal(SIGCHLD,SIG_DFL);p=fork();
    if(p<0)return 2;if(!p){alarm(10);_exit(run());}
    if(wait3(&s,0,NULL)!=p)return 2;
    return WIFEXITED(s)?WEXITSTATUS(s):3;
}
