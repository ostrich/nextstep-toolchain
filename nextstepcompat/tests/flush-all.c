/* Verify all native streams, including the dynamic stream table. 0BSD. */
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <errno.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL flush line %d errno %d\n",__LINE__,errno); return 1; } } while (0)
int main(void)
{
 FILE *files[32], *bad;
 struct stat st;
 struct sigaction ignore, previous;
 int i, pipefd[2];
 CHECK(fflush(NULL)==0);
 for(i=0;i<32;i++) {
  files[i]=tmpfile();CHECK(files[i]!=NULL);
  CHECK(setvbuf(files[i],NULL,_IOFBF,512)==0);
  CHECK(fputs("hello",files[i])!=EOF);
 }
 CHECK(fflush(NULL)==0);
 for(i=0;i<32;i++) { CHECK(fstat(fileno(files[i]),&st)==0);CHECK(st.st_size==5); }
 CHECK(fseek(files[0],0,SEEK_SET)==0);CHECK(fgetc(files[0])=='h');
 CHECK(fflush(NULL)==0);CHECK(fgetc(files[0])=='e');
 for(i=0;i<32;i++)CHECK(fclose(files[i])==0);
 sigemptyset(&ignore.sa_mask);ignore.sa_flags=0;ignore.sa_handler=(void (*)(int))SIG_IGN;
 CHECK(sigaction(SIGPIPE,&ignore,&previous)==0);
 CHECK(pipe(pipefd)==0);CHECK(close(pipefd[0])==0);
 bad=fdopen(pipefd[1],"w");CHECK(bad!=NULL);
 CHECK(setvbuf(bad,NULL,_IOFBF,512)==0);CHECK(fputs("error",bad)!=EOF);
 errno=0;CHECK(fflush(NULL)==EOF);CHECK(errno==EPIPE);CHECK(ferror(bad));
 fclose(bad);CHECK(sigaction(SIGPIPE,&previous,NULL)==0);
 puts("PASS flush-all static/dynamic streams, read state and write errors");
 return 0;
}
