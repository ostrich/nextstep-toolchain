/* IPv4 adapter regression tests. SPDX-License-Identifier: 0BSD */
#include <netdb.h>
#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <ctype.h>
#include <sys/select.h>

static unsigned checks, failures;
static volatile sig_atomic_t pipe_signals;
static void pipe_notice(int signal_number) { (void)signal_number; ++pipe_signals; }
#define CHECK(c) do { ++checks; if (!(c)) { ++failures; printf("FAIL line %d: %s\n",__LINE__,#c); } } while (0)
static void addresses(void)
{
  const char *valid[] = {"0.0.0.0","127.0.0.1","255.255.255.255","192.0.2.37"};
  const char *invalid[] = {"","1","127.1","1.2.3","1.2.3.4.5","256.0.0.1","01.2.3.4","1.2.3.-1"," 1.2.3.4","1.2.3.4 ","1.2.3.0x4","1..2.3","::1","\xff.2.3.4"};
  struct in_addr address;
  char text[INET_ADDRSTRLEN];
  unsigned i;
  for (i=0;i<sizeof(valid)/sizeof(valid[0]);++i) {
    CHECK(inet_pton(AF_INET,valid[i],&address)==1);
    CHECK(inet_ntop(AF_INET,&address,text,sizeof(text))==text);
    CHECK(!strcmp(text,valid[i]));
  }
  for (i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) CHECK(inet_pton(AF_INET,invalid[i],&address)==0);
  {
    struct in6_addr v6;
    const char *samples[]={"::","::1","2001:db8::1","::ffff:192.0.2.37","2001:db8:0:1:2:3:4:5"};
    char output[INET6_ADDRSTRLEN];
    for(i=0;i<sizeof(samples)/sizeof(samples[0]);++i) {
      struct in6_addr copy;
      CHECK(inet_pton(AF_INET6,samples[i],&v6)==1);
      CHECK(inet_ntop(AF_INET6,&v6,output,sizeof(output))==output);
      CHECK(inet_pton(AF_INET6,output,&copy)==1 && !memcmp(&v6,&copy,sizeof(v6)));
    }
    CHECK(inet_pton(AF_INET6,"1::2::3",&v6)==0);
    CHECK(inet_pton(AF_INET6,"12345::",&v6)==0);
    CHECK(inet_pton(AF_INET6,"1:2:3:4:5:6:7:8:9",&v6)==0);
    CHECK(inet_pton(AF_INET6,"::ffff:256.0.0.1",&v6)==0);
    CHECK(inet_pton(AF_INET6,"::ffff:192.0.2.37",&v6)==1 && IN6_IS_ADDR_V4MAPPED(&v6));
    errno=0;CHECK(!inet_ntop(AF_INET6,&v6,output,2) && errno==ENOSPC);
    errno=0;CHECK(socket(AF_INET6,SOCK_STREAM,0)==-1 && (errno==EAFNOSUPPORT || errno==EPROTONOSUPPORT));
  }
  errno=0; CHECK(inet_pton(AF_UNSPEC,"127.0.0.1",&address)==-1 && errno==EAFNOSUPPORT);
  errno=0; CHECK(!inet_ntop(AF_UNSPEC,&address,text,sizeof(text)) && errno==EAFNOSUPPORT);
  CHECK(inet_pton(AF_INET,"192.0.2.37",&address)==1);
  errno=0; CHECK(!inet_ntop(AF_INET,&address,text,0) && errno==ENOSPC);
  errno=0; CHECK(!inet_ntop(AF_INET,&address,text,-1) && errno==EINVAL);
  errno=0; CHECK(!inet_ntop(AF_INET,&address,text,5) && errno==ENOSPC);
}
static void numeric_resolution(void)
{
  struct addrinfo hints={0},*list=0,*p;
  int result, count=0, tcp=0, udp=0;
  char host[32],service[16];
  hints.ai_family=AF_INET;hints.ai_flags=AI_NUMERICHOST|AI_NUMERICSERV|AI_CANONNAME;
  result=getaddrinfo("192.0.2.37","65535",&hints,&list);
  CHECK(result==0 && list!=0);
  for (p=list;p;p=p->ai_next) {
    struct sockaddr_in *a=(struct sockaddr_in *)p->ai_addr;
    CHECK(p->ai_family==AF_INET && p->ai_addrlen==sizeof(*a));
    CHECK(a->sin_family==AF_INET && ntohs(a->sin_port)==65535);
    CHECK(ntohl(a->sin_addr.s_addr)==0xc0000225UL);
    CHECK(getnameinfo(p->ai_addr,p->ai_addrlen,host,sizeof(host),service,sizeof(service),NI_NUMERICHOST|NI_NUMERICSERV)==0);
    CHECK(!strcmp(host,"192.0.2.37") && !strcmp(service,"65535"));
    if(p->ai_socktype==SOCK_STREAM && p->ai_protocol==IPPROTO_TCP) ++tcp;
    if(p->ai_socktype==SOCK_DGRAM && p->ai_protocol==IPPROTO_UDP) ++udp;
    if(!count) CHECK(p->ai_canonname && !strcmp(p->ai_canonname,"192.0.2.37"));
    else CHECK(p->ai_canonname==0);
    ++count;
  }
  CHECK(count==2 && tcp==1 && udp==1);
  freeaddrinfo(list);
  hints.ai_flags=AI_NUMERICSERV|AI_PASSIVE;hints.ai_socktype=SOCK_STREAM;
  list=0;CHECK(getaddrinfo(0,"0",&hints,&list)==0);
  if(list) {CHECK(((struct sockaddr_in *)list->ai_addr)->sin_addr.s_addr==htonl(INADDR_ANY));CHECK(!list->ai_next);freeaddrinfo(list);}
  hints.ai_flags=AI_NUMERICSERV;hints.ai_protocol=IPPROTO_UDP;hints.ai_socktype=0;
  list=0;CHECK(getaddrinfo(0,"53",&hints,&list)==0);
  if(list) {CHECK(((struct sockaddr_in *)list->ai_addr)->sin_addr.s_addr==htonl(INADDR_LOOPBACK));CHECK(list->ai_socktype==SOCK_DGRAM && !list->ai_next);freeaddrinfo(list);}
}
static void errors(void)
{
  struct addrinfo hints={0},*list=(void *)1;
  struct sockaddr_in address={0};
  char host[16]="unchanged",service[16]="unchanged";
  CHECK(getaddrinfo(0,0,0,&list)==EAI_NONAME && !list);
  CHECK(getaddrinfo("127.0.0.1","80",0,0)==EAI_FAIL);
  hints.ai_family=AF_UNIX;CHECK(getaddrinfo("127.0.0.1","80",&hints,&list)==EAI_FAMILY && !list);
  hints.ai_family=AF_INET6;CHECK(getaddrinfo("::1","80",&hints,&list)==EAI_FAMILY && !list);
  hints.ai_family=AF_INET;hints.ai_flags=0x40000000;CHECK(getaddrinfo("127.0.0.1","80",&hints,&list)==EAI_BADFLAGS && !list);
  hints.ai_flags=AI_CANONNAME;CHECK(getaddrinfo(0,"80",&hints,&list)==EAI_BADFLAGS);
  hints.ai_flags=AI_NUMERICHOST;CHECK(getaddrinfo("127.1","80",&hints,&list)==EAI_NONAME);
  hints.ai_flags=AI_NUMERICHOST|AI_NUMERICSERV;
  CHECK(getaddrinfo("127.0.0.1","named",&hints,&list)==EAI_NONAME);
  CHECK(getaddrinfo("127.0.0.1","+80",&hints,&list)==EAI_NONAME);
  CHECK(getaddrinfo("127.0.0.1"," 80",&hints,&list)==EAI_NONAME);
  CHECK(getaddrinfo("127.0.0.1","65536",&hints,&list)==EAI_SERVICE);
  CHECK(getaddrinfo("127.0.0.1","999999999999999999999",&hints,&list)==EAI_SERVICE);
  hints.ai_socktype=SOCK_RAW;CHECK(getaddrinfo("127.0.0.1","80",&hints,&list)==EAI_SOCKTYPE);
  hints.ai_socktype=SOCK_STREAM;hints.ai_protocol=IPPROTO_UDP;CHECK(getaddrinfo("127.0.0.1","80",&hints,&list)==EAI_SERVICE);
  address.sin_family=AF_INET;address.sin_port=htons(12345);inet_pton(AF_INET,"192.0.2.37",&address.sin_addr);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),service,2,NI_NUMERICHOST|NI_NUMERICSERV)==EAI_OVERFLOW);
  CHECK(!strcmp(host,"unchanged") && !strcmp(service,"unchanged"));
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),0,0,0,0,0)==EAI_NONAME);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,-1,0,0,0)==EAI_OVERFLOW);
  CHECK(getnameinfo((struct sockaddr *)&address,1,host,sizeof(host),0,0,NI_NUMERICHOST)==EAI_FAMILY);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),0,0,0x40000000)==EAI_BADFLAGS);
  CHECK(strstr(gai_strerror(EAI_AGAIN),"Temporary")!=0);
  CHECK(strstr(gai_strerror(12345),"Unknown")!=0);
  freeaddrinfo(0);
}
static any_t worker(any_t unused)
{
  int i;
  const char *node="192.0.2.37", *expected="192.0.2.37";
#ifdef MOCK_RESOLVER
  node = (unsigned long)unused & 1 ? "mockhost2" : "mockhost";
  expected = (unsigned long)unused & 1 ? "20.20.30.40" : "10.20.30.40";
#else
  (void)unused;
#endif
  for(i=0;i<100;++i) {
    struct addrinfo h={0},*p=0;
    char host[32],service[16];
    h.ai_family=AF_INET;h.ai_socktype=SOCK_STREAM;h.ai_flags=AI_NUMERICSERV;
#ifndef MOCK_RESOLVER
    h.ai_flags|=AI_NUMERICHOST;
#endif
    if(getaddrinfo(node,"12345",&h,&p) || !p) return (any_t)1;
    if(getnameinfo(p->ai_addr,p->ai_addrlen,host,sizeof(host),service,sizeof(service),NI_NUMERICHOST|NI_NUMERICSERV) || strcmp(host,expected) || strcmp(service,"12345")) {freeaddrinfo(p);return (any_t)2;}
    freeaddrinfo(p);
  }
  return 0;
}
#ifdef MOCK_RESOLVER
void mock_checks(void);
#endif
int main(int argc, char **argv)
{
  cthread_t threads[4];int i;
  alarm(45);
  for(i=-100;i<356;++i) {
    CHECK(!!isascii(i)==(i>=0 && i<128));CHECK(!!(isascii)(i)==(i>=0 && i<128));
    CHECK(toascii(i)==(i&127));CHECK((toascii)(i)==(i&127));
  }
  i=0;CHECK(isascii(i++) && i==1);
  i=getpagesize();CHECK(i>=1024 && (i & (i-1))==0);
  {
    unsigned char buffer[64];
    memset(buffer,0xa5,sizeof(buffer));
    explicit_bzero(buffer+7,41);
    for(i=0;i<64;++i) CHECK(buffer[i]==(i>=7 && i<48 ? 0 : 0xa5));
    explicit_bzero(buffer,0);
    CHECK(buffer[0]==0xa5);
  }
  {
    int pair[2];
    void (*previous)(int)=signal(SIGPIPE,pipe_notice);
    CHECK(socketpair(AF_UNIX,SOCK_STREAM,0,pair)==0);
    {
      fd_set descriptors;
      struct timeval timeout={0,0};
      FD_ZERO(&descriptors);FD_SET(pair[0],&descriptors);
      CHECK(select(pair[0]+1,&descriptors,0,0,&timeout)==0);
      CHECK(!FD_ISSET(pair[0],&descriptors));
    }
    CHECK(shutdown(pair[1],SHUT_RDWR)==0);
    close(pair[1]);errno=0;
    CHECK(send(pair[0],"x",1,0)==-1 && errno==EPIPE && pipe_signals==1);
    close(pair[0]);signal(SIGPIPE,previous);
  }
  addresses();numeric_resolution();errors();
  if(argc>1 && !strcmp(argv[1],"--native-databases")) {
    struct addrinfo hints={0},*list=0;
    hints.ai_family=AF_INET;hints.ai_socktype=SOCK_STREAM;hints.ai_flags=AI_CANONNAME;
    CHECK(getaddrinfo("localhost","domain",&hints,&list)==0 && list);
    if(list) {
      CHECK(ntohs(((struct sockaddr_in *)list->ai_addr)->sin_port)==53);
      CHECK(list->ai_canonname!=0);
      freeaddrinfo(list);
    }
    hints.ai_flags=AI_ADDRCONFIG|AI_NUMERICHOST|AI_NUMERICSERV;
    CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==0 && list);
    freeaddrinfo(list);
  }
  (void)pthread_self();
  for(i=0;i<4;++i) {threads[i]=cthread_fork(worker,(any_t)(unsigned long)i);CHECK(threads[i]!=0);}
  for(i=0;i<4;++i) if(threads[i]) CHECK(cthread_join(threads[i])==0);
#ifdef MOCK_RESOLVER
  mock_checks();
#endif
  printf("IPv4 adapters: %u checks, %u failures\n",checks,failures);
  return failures!=0;
}

#ifdef MOCK_RESOLVER
#include "mock-resolver.c"
#endif
