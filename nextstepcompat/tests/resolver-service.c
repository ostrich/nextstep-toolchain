/* getnameinfo's NI flags must not be interpreted as AI flags. 0BSD. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL resolver line %d\n",__LINE__); return 1; } } while (0)
int main(void)
{
 struct sockaddr_in a;
 char service[8], host[32];
 int flags;
 memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(22220);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 for (flags=0;flags<16;flags++) {
  if (!(flags&NI_NUMERICSERV))continue;
  CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),0,0,service,sizeof(service),flags)==0);
  CHECK(!strcmp(service,"22220"));
 }
 CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),host,sizeof(host),0,0,NI_NUMERICHOST)==0);
 CHECK(!strcmp(host,"127.0.0.1"));
 CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),host,sizeof(host),service,sizeof(service),NI_NUMERICHOST|NI_NUMERICSERV)==0);
 CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),0,0,service,2,NI_NUMERICSERV)==EAI_OVERFLOW);
 CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),0,0,service,sizeof(service),16)==EAI_BADFLAGS);
 CHECK(getnameinfo((struct sockaddr *)&a,sizeof(a),0,0,0,0,0)==EAI_NONAME);
 puts("PASS numeric service-only resolver flags and boundaries");return 0;
}
