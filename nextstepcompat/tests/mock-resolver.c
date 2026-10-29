/* Deterministic native database fixtures for network.c. SPDX-License-Identifier: 0BSD */
#include <stdarg.h>
#include <sys/ioctl.h>
#include <net/if.h>
int ns33_test_h_errno;
static int interface_mode=1;
static char native_name[64];
static char ip1[4]={10,20,30,40}, ip2[4]={1,2,3,4};
static char *native_addresses[]={ip1,ip2,0};
static char *native_aliases[]={0};
static struct hostent native_host={native_name,native_aliases,AF_INET,4,native_addresses};
static struct servent native_service={"mockservice",native_aliases,0,"tcp"};
struct hostent *ns33_test_gethostbyname(char *name)
{
  if(!strcmp(name,"temporary")) {ns33_test_h_errno=TRY_AGAIN;return 0;}
  if(!strcmp(name,"failed")) {ns33_test_h_errno=NO_RECOVERY;return 0;}
  if(strcmp(name,"mockhost") && strcmp(name,"mockhost2")) {ns33_test_h_errno=HOST_NOT_FOUND;return 0;}
  ip1[0]=!strcmp(name,"mockhost2")?20:10;
  ip2[0]=ip1[0]/10;
  cthread_yield();
  strcpy(native_name,"resolved.example");return &native_host;
}
struct hostent *ns33_test_gethostbyaddr(char *address,int length,int family)
{
  if(length!=4 || family!=AF_INET || memcmp(address,ip1,4)) {ns33_test_h_errno=HOST_NOT_FOUND;return 0;}
  strcpy(native_name,"resolved.example");return &native_host;
}
struct servent *ns33_test_getservbyname(char *name,char *protocol)
{
  if(strcmp(name,"mockservice") && strcmp(name,"999999service")) return 0;
  native_service.s_port=htons(5353);native_service.s_proto=protocol;
  return &native_service;
}
struct servent *ns33_test_getservbyport(int port,char *protocol)
{
  strcpy(native_name,"overwritten");
  if(port!=htons(5353)) return 0;
  native_service.s_port=port;native_service.s_proto=protocol;
  return &native_service;
}
void mock_checks(void)
{
  struct addrinfo hints={0},*list=0,*p;
  struct sockaddr_in address={0};
  char host[64],service[32];
  int count=0;
  hints.ai_flags=AI_CANONNAME;
  CHECK(getaddrinfo("mockhost","mockservice",&hints,&list)==0);
  for(p=list;p;p=p->ai_next) {
    struct sockaddr_in *a=(struct sockaddr_in *)p->ai_addr;
    CHECK(ntohs(a->sin_port)==5353);
    CHECK(ntohl(a->sin_addr.s_addr)==(count<2?0x0a141e28UL:0x01020304UL));
    if(!count) CHECK(p->ai_canonname && !strcmp(p->ai_canonname,"resolved.example"));
    else CHECK(!p->ai_canonname);
    ++count;
  }
  CHECK(count==4);freeaddrinfo(list);
  CHECK(getaddrinfo("temporary","80",0,&list)==EAI_AGAIN && !list);
  CHECK(getaddrinfo("failed","80",0,&list)==EAI_FAIL && !list);
  CHECK(getaddrinfo("missing","80",0,&list)==EAI_NONAME && !list);
  CHECK(getaddrinfo("127.0.0.1","unknown-service",0,&list)==EAI_SERVICE && !list);
  CHECK(getaddrinfo("127.0.0.1","999999service",0,&list)==0);freeaddrinfo(list);
  address.sin_family=AF_INET;address.sin_port=htons(5353);memcpy(&address.sin_addr,ip1,4);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),service,sizeof(service),0)==0);
  CHECK(!strcmp(host,"resolved.example") && !strcmp(service,"mockservice"));
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),service,sizeof(service),NI_NUMERICHOST|NI_NUMERICSERV)==0);
  CHECK(!strcmp(host,"10.20.30.40") && !strcmp(service,"5353"));
  inet_pton(AF_INET,"192.0.2.37",&address.sin_addr);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),service,sizeof(service),NI_NAMEREQD)==EAI_NONAME);
  CHECK(getnameinfo((struct sockaddr *)&address,sizeof(address),host,sizeof(host),service,sizeof(service),0)==0);
  CHECK(!strcmp(host,"192.0.2.37"));
  memset(&hints,0,sizeof(hints));hints.ai_flags=AI_ADDRCONFIG|AI_NUMERICHOST|AI_NUMERICSERV;
  interface_mode=0;CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==EAI_NONAME && !list);
  interface_mode=1;CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==0 && list);freeaddrinfo(list);
  interface_mode=2;errno=0;CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==EAI_SYSTEM && errno==EACCES && !list);
  interface_mode=3;errno=0;CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==EAI_SYSTEM && errno==EOVERFLOW && !list);
  interface_mode=4;errno=0;CHECK(getaddrinfo("192.0.2.37","80",&hints,&list)==EAI_SYSTEM && errno==EIO && !list);
  interface_mode=1;
}

int ns33_test_ioctl(int fd,long request,...)
{
  va_list ap;
  void *value;
  (void)fd;
  va_start(ap,request);value=va_arg(ap,void *);va_end(ap);
  if(interface_mode==2) {errno=EACCES;return -1;}
  if(request==SIOCGIFCONF) {
    struct ifconf *configuration=value;
    struct ifreq *interface=configuration->ifc_req;
    struct sockaddr_in *address=(struct sockaddr_in *)&interface->ifr_addr;
    if(interface_mode==3) return 0;
    if(interface_mode==4) {configuration->ifc_len=sizeof(*interface)-1;return 0;}
    memset(interface,0,sizeof(*interface));strcpy(interface->ifr_name,"en0");
    address->sin_family=AF_INET;address->sin_addr.s_addr=htonl(0x0a000001);
    configuration->ifc_len=sizeof(*interface);return 0;
  }
  if(request==SIOCGIFFLAGS) {
    ((struct ifreq *)value)->ifr_flags=IFF_UP|(interface_mode==0?IFF_LOOPBACK:0);
    return 0;
  }
  errno=EINVAL;return -1;
}
