/* Regressions exposed by shell and transfer applications. SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <grp.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <sys/wait.h>
extern int native_getgroups(int, int *) __asm__("_getgroups");
extern pid_t native_getpgrp(pid_t) __asm__("_getpgrp");
int main(void) {
 char fields[]="a,,b:", *cursor=fields, buf[8]={0};
 const char *expected[]={"a","","b",""};
 int i,count,oldcount,native[16],ss_family=AF_INET;
 gid_t old[16],newgroups[2]={20,1000};
 struct sockaddr_storage address;
 if(sizeof(address)!=128 || offsetof(struct sockaddr_storage,ss_family)!=0)return 1;
 address.ss_family=ss_family;
 for(i=0;i<4;i++){char *part=strsep(&cursor,",:");if(!part || strcmp(part,expected[i]))return 2;}
 if(cursor || strsep(&cursor,","))return 3;
 if(memccpy(buf,"abcd",'c',4)!=buf+3 || memcmp(buf,"abc",3) || buf[3])return 4;
 if(memccpy(buf,"abcd",'x',4) || memcmp(buf,"abcd",4))return 5;
 if(memccpy(buf,"a",'a',0))return 6;
 oldcount=getgroups(16,old);if(oldcount<0)return 7;
 if(setgroups(2,newgroups))return 8;
 count=native_getgroups(16,native);
 if(setgroups(oldcount,old))return 9;
 if(count!=2 || native[0]!=20 || native[1]!=1000)return 10;
 errno=0;if(setgroups(17,newgroups)!=-1 || errno!=EINVAL)return 11;
 errno=0;if(setgroups(1,NULL)!=-1 || errno!=EFAULT)return 12;
 if(setreuid(-1,-1) || setregid(-1,-1))return 13;
 if(getpgrp()!=native_getpgrp(0) || getpgrp()<=0)return 14;
 { int status, child=fork();
   if(child<0)return 15;
   if(!child) _exit(setpgid(0,0) || getpgrp()!=getpid());
   if(wait4(child,&status,0,0)!=child || !WIFEXITED(status) || WEXITSTATUS(status))return 16;
 }
 errno=0;if(setpgid(-1,0)!=-1 || errno!=EINVAL)return 17;
 errno=0;if(setpgid(0,-1)!=-1 || errno!=EINVAL)return 18;
 printf("COMPAT shell/group/string/socket PASS\n");return 0;
}
