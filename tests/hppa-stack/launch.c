/* Isolate large automatic frames from Bash. SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifndef CAPTURE_SIZE
#define CAPTURE_SIZE 16384
#endif
int main(int argc,char **argv)
{
  volatile char pad[CAPTURE_SIZE];
  char *env[]={"PATH=/bin:/usr/bin:/usr/ucb","LC_ALL=C","HOME=/private/tmp",0};
  char *args[]={"/private/tmp/bash-suite/argv-dump","--noprofile","--norc","-c","printf '%s\\n' one two three",0};
  int i,s=-1;pid_t p;
  setbuf(stdout,0);
  for(i=0;i<CAPTURE_SIZE;i++)pad[i]=(char)(i%127);
  for(i=0;i<CAPTURE_SIZE;i++)if(pad[i]!=(char)(i%127)){printf("PADFAIL:%d\n",i);return 1;}
  printf("PADPASS:%d pad=%p args=%p env=%p\n",CAPTURE_SIZE,(void *)pad,(void *)args,(void *)env);
  if(argc>1 && strcmp(argv[1],"fork")==0){p=fork();if(p<0)return 2;if(p){wait3((union wait *)&s,0,0);printf("CHILD_STATUS:%x\n",s);return s!=0;}}
  for(i=0;args[i];i++)printf("BEFORE%d[%lu]:%s\n",i,(unsigned long)strlen(args[i]),args[i]);
  alarm(15);execve(args[0],args,env);perror("execve");return 3;
}
