/* Target signal contract tests. SPDX-License-Identifier: 0BSD */
#define _NEXT_SOURCE 1
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
static int checks, failures;
static volatile sig_atomic_t caught, handler_self, handler_extra;
static void check(int ok,const char *name)
{
  ++checks;
  if(!ok) { ++failures;printf("FAIL %s errno=%d\n",name,errno); }
}
static void handler(int sig)
{
  int saved=errno;
  sigset_t mask;
  if(sig==SIGUSR1) ++caught;
  sigprocmask(SIG_BLOCK,NULL,&mask);
  handler_self=((unsigned)mask & (1U<<(SIGUSR1-1)))!=0;
  handler_extra=((unsigned)mask & (1U<<(SIGUSR2-1)))!=0;
  errno=saved;
}
static void reap(pid_t child)
{
  int status;
  int result;
  do { result=wait3(&status,0,NULL); } while(result<0 && errno==EINTR);
  check(result==child && WIFEXITED(status) && WEXITSTATUS(status)==0,"child exit");
}
static void interrupted_read(int restart)
{
  int fd[2], result, error;
  char c=0;
  pid_t child;
  struct sigaction action;
  memset(&action,0,sizeof(action));
  action.sa_handler=handler;action.sa_flags=restart?SA_RESTART:0;
  check(sigaction(SIGUSR1,&action,NULL)==0,"read handler");
  if(pipe(fd)) {check(0,"pipe");return;}
  child=fork();
  if(child==0) {
    close(fd[0]);sleep(1);kill(getppid(),SIGUSR1);
    sleep(1);result=write(fd[1],"x",1);close(fd[1]);_exit(result==1?0:1);
  }
  if(child<0) {check(0,"fork");close(fd[0]);close(fd[1]);return;}
  close(fd[1]);errno=0;result=read(fd[0],&c,1);error=errno;
  if(restart) check(result==1 && c=='x',"SA_RESTART resumes read");
  else {
    check(result==-1 && error==EINTR,"zero flags interrupts read");
    do {result=read(fd[0],&c,1);} while(result<0 && errno==EINTR);
    check(result==1 && c=='x',"read after EINTR");
  }
  close(fd[0]);reap(child);
}
int main(void)
{
  sigset_t set,old,current,pending,alias;
  struct sigaction action,previous,query;
  struct sigvec bsd;
  int s, before, r, e;
  setbuf(stdout,NULL);alarm(25);
  if(getuid()==0 && (setgid(1) || setuid(1))) {perror("drop privileges");return 2;}
  check(getuid()!=0,"ordinary user");
  check(sizeof(sigset_t)==4,"native sigset layout");
  check(sigemptyset(&set)==0 && set==0,"empty set");
  for(s=1;s<NSIG;s++) {
    check(sigismember(&set,s)==0,"initial membership");
    check(sigaddset(&set,s)==0 && sigismember(&set,s)==1,"add membership");
    check(sigdelset(&set,s)==0 && sigismember(&set,s)==0,"delete membership");
  }
  check(sigfillset(&set)==0,"fill set");
  for(s=1;s<NSIG;s++)check(sigismember(&set,s)==1,"filled membership");
  for(s=-1;s<=NSIG;s+=s<1?1:NSIG-1) {
    if(s==1)continue;
    alias=set;errno=0;check(sigaddset(&set,s)==-1 && errno==EINVAL && set==alias,"invalid add");
    errno=0;check(sigdelset(&set,s)==-1 && errno==EINVAL && set==alias,"invalid delete");
    errno=0;check(sigismember(&set,s)==-1 && errno==EINVAL,"invalid membership");
  }
  check(sigprocmask(999,NULL,&old)==0,"query ignores how");
  alias=old;errno=0;check(sigprocmask(999,&set,&alias)==-1 && errno==EINVAL && alias==old,"invalid mask operation");
  memset(&action,0,sizeof(action));action.sa_handler=handler;
  sigemptyset(&action.sa_mask);sigaddset(&action.sa_mask,SIGUSR2);
  action.sa_flags=SA_RESTART;
  check(sigaction(SIGUSR1,&action,&previous)==0,"install action");
  check(sigaction(SIGUSR1,NULL,&query)==0 && query.sa_handler==handler &&
        query.sa_mask==action.sa_mask && query.sa_flags==SA_RESTART,"query action");
  check(sigvec(SIGUSR1,NULL,&bsd)==0 && !(bsd.sv_flags&SV_INTERRUPT),"BSD restart flag inverse");
  sigemptyset(&set);sigaddset(&set,SIGUSR1);
  check(sigprocmask(SIG_BLOCK,&set,&current)==0 && current==old,"block returns previous mask");
  check(kill(getpid(),SIGUSR1)==0 && caught==0,"blocked delivery");
  check(sigpending(&pending)==0 && sigismember(&pending,SIGUSR1)==1,"pending signal reported");
  alias=set;
  check(sigprocmask(SIG_UNBLOCK,&alias,&alias)==0 && sigismember(&alias,SIGUSR1)==1,"unblock alias");
  check(caught==1,"pending delivered on unblock");
  check(handler_self && handler_extra,"handler mask includes self and action mask");
  check(sigpending(&pending)==0 && sigismember(&pending,SIGUSR1)==0,"pending cleared");
  check(sigprocmask(SIG_BLOCK,&set,NULL)==0,"block for suspend");
  before=caught;kill(getpid(),SIGUSR1);sigprocmask(SIG_BLOCK,NULL,&current);
  errno=0;r=sigsuspend(&old);e=errno;
  check(r==-1 && e==EINTR && caught==before+1,"suspend delivers pending signal");
  sigprocmask(SIG_BLOCK,NULL,&pending);check(pending==current,"suspend restores previous mask");
  check(sigprocmask(SIG_SETMASK,&old,NULL)==0,"restore original mask");
  action.sa_flags=SA_ONSTACK|SA_RESTART;
  check(sigaction(SIGUSR1,&action,&action)==0 && action.sa_flags==SA_RESTART,"action alias");
  sigaction(SIGUSR1,NULL,&query);
  check(query.sa_flags==(SA_ONSTACK|SA_RESTART),"onstack flag round trip");
  action=query;action.sa_flags=SA_NOCLDSTOP;
  errno=0;check(sigaction(SIGUSR1,&action,NULL)==-1 && errno==EINVAL,"reject unsupported NOCLDSTOP");
  action.sa_flags=0x40000000;
  errno=0;check(sigaction(SIGUSR1,&action,NULL)==-1 && errno==EINVAL,"reject unknown action flags");
  sigaction(SIGUSR1,NULL,&action);
  check(action.sa_flags==query.sa_flags,"rejected action leaves state unchanged");
  errno=0;check(sigaction(SIGKILL,&action,NULL)==-1 && errno==EINVAL,"uncatchable signal");
  sigfillset(&set);sigprocmask(SIG_BLOCK,&set,NULL);sigprocmask(SIG_BLOCK,NULL,&current);
  check(sigismember(&current,SIGKILL)==0 && sigismember(&current,SIGSTOP)==0,"uncatchable signals unblocked");
  sigprocmask(SIG_SETMASK,&old,NULL);
  interrupted_read(0);interrupted_read(1);
  sigaction(SIGUSR1,&previous,NULL);sigprocmask(SIG_SETMASK,&old,NULL);alarm(0);
  printf("POSIX signals: %d checks, %d failures\n",checks,failures);
  return failures!=0;
}
