/* Standard mkfifo contract test over real filesystem FIFOs.
   Run in disposable guests as root; all FIFO operations run after dropping
   to uid/gid 1. The parent directory is created and transferred first. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern void bzero(void *, unsigned long);
extern int select(int, fd_set *, fd_set *, fd_set *, struct timeval *);
static int checks, failures;
static void check(int ok, const char *what) {
    ++checks;
    printf("%s %s (errno=%d)\n", ok ? "PASS" : "FAIL", what, errno);
    if (!ok) ++failures;
}
int main(void) {
    char dir[100], path[130], buf[8];
    struct stat st;
    struct timeval tv;
    fd_set ready;
    int rd=-1, wr=-1, r, e;
    setbuf(stdout, NULL);
    alarm(20);
    sprintf(dir, "/private/tmp/fifo-probe-%ld", (long)getpid());
    if (mkdir(dir, 0700)) { perror("mkdir"); return 2; }
    if (getuid()==0 && (chown(dir,1,1) || setgid(1) || setuid(1))) {
        perror("drop privileges"); rmdir(dir); return 2;
    }
    printf("FIFO probe uid=%ld gid=%ld\n", (long)getuid(), (long)getgid());
    check(getuid()!=0, "ordinary user");
    sprintf(path, "%s/pipe", dir);
    umask(0027);
    errno=0; r=mkfifo(path, 0666); e=errno;
    printf("mkfifo result=%d errno=%d (%s)\n", r,e,strerror(e));
    check(r==0, "create FIFO");
    if (r) goto done;
    check(stat(path,&st)==0 && S_ISFIFO(st.st_mode) && (st.st_mode&0777)==0640,
          "FIFO type and umask");
    errno=0; wr=open(path,O_WRONLY|O_NONBLOCK); e=errno;
    check(wr==-1 && e==ENXIO, "nonblocking writer without reader");
    if(wr>=0) { close(wr);wr=-1; }
    rd=open(path,O_RDONLY|O_NONBLOCK);
    check(rd>=0, "nonblocking reader");
    if(rd<0) goto done;
    check(read(rd,buf,sizeof(buf))==0, "EOF with no writer");
    wr=open(path,O_WRONLY|O_NONBLOCK);
    check(wr>=0, "writer with reader");
    if(wr<0) goto done;
    errno=0; r=read(rd,buf,sizeof(buf));e=errno;
    check(r==-1 && (e==EAGAIN || e==EWOULDBLOCK), "empty live FIFO would block");
    check(write(wr,"fifo",4)==4, "write");
    FD_ZERO(&ready);FD_SET(rd,&ready);tv.tv_sec=1;tv.tv_usec=0;
    check(select(rd+1,&ready,NULL,NULL,&tv)==1 && FD_ISSET(rd,&ready), "select readable");
    r=read(rd,buf,sizeof(buf));
    check(r==4 && !memcmp(buf,"fifo",4), "read matches write");
    close(wr);wr=-1;
    check(read(rd,buf,sizeof(buf))==0, "EOF after writer closes");
    wr=open(path,O_WRONLY|O_NONBLOCK);
    check(wr>=0, "reopen writer");
    close(rd);rd=-1;
    signal(SIGPIPE,SIG_IGN);
    errno=0;r=write(wr,"x",1);e=errno;
    check(r==-1 && e==EPIPE, "broken pipe");
done:
    if(wr>=0)close(wr);
    if(rd>=0)close(rd);
    unlink(path);rmdir(dir);
    printf("mkfifo: %d checks, %d failures\n",checks,failures);
    return failures!=0;
}
