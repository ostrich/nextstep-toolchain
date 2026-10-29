/* IPv4 name resolution using the native BSD/NetInfo databases.
   SPDX-License-Identifier: 0BSD */
#include <netdb.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>
#include <errno.h>

static pthread_mutex_t resolver_lock = PTHREAD_MUTEX_INITIALIZER;

static int ipv4_configured(void)
{
  int fd = socket(AF_INET,SOCK_DGRAM,0), result = -1, saved = 0;
  unsigned capacity;
  if (fd < 0) return -1;
  for (capacity = 16; capacity <= 256; capacity *= 2) {
    struct ifreq *interfaces = calloc(capacity,sizeof(*interfaces));
    struct ifconf configuration;
    unsigned i, count;
    if (!interfaces) { saved = ENOMEM; break; }
    configuration.ifc_len = capacity * sizeof(*interfaces);
    configuration.ifc_buf = (char *)interfaces;
    if (ioctl(fd,SIOCGIFCONF,&configuration) < 0) {
      saved = errno; free(interfaces); break;
    }
    if (configuration.ifc_len < 0 || configuration.ifc_len % sizeof(*interfaces)) {
      saved = EIO; free(interfaces); break;
    }
    count = configuration.ifc_len / sizeof(*interfaces);
    if (count >= capacity) { free(interfaces); continue; }
    result = 0;
    for (i = 0; i < count; ++i) {
      struct ifreq flags;
      struct sockaddr_in *address = (struct sockaddr_in *)&interfaces[i].ifr_addr;
      if (address->sin_family != AF_INET || !address->sin_addr.s_addr) continue;
      memset(&flags,0,sizeof(flags));
      memcpy(flags.ifr_name,interfaces[i].ifr_name,sizeof(flags.ifr_name));
      if (ioctl(fd,SIOCGIFFLAGS,&flags) < 0) { saved = errno; result = -1; break; }
      if ((flags.ifr_flags & IFF_UP) && !(flags.ifr_flags & IFF_LOOPBACK)) { result = 1; break; }
    }
    free(interfaces);
    break;
  }
  if (result < 0 && !saved) saved = EOVERFLOW;
  close(fd);
  if (saved) errno = saved;
  return result;
}


void ns33_freeaddrinfo(struct addrinfo *node)
{
  while (node) {
    struct addrinfo *next = node->ai_next;
    free(node->ai_addr);
    free(node->ai_canonname);
    free(node);
    node = next;
  }
}

static int append_address(struct addrinfo ***tail, in_addr_t address,
                          unsigned short port, int type, int protocol,
                          int flags, const char *canonical)
{
  struct addrinfo *node = calloc(1,sizeof(*node));
  struct sockaddr_in *socket_address;
  if (!node) return EAI_MEMORY;
  socket_address = calloc(1,sizeof(*socket_address));
  if (!socket_address) { free(node); return EAI_MEMORY; }
  socket_address->sin_family = AF_INET;
  socket_address->sin_port = port;
  socket_address->sin_addr.s_addr = address;
  node->ai_flags = flags;
  node->ai_family = AF_INET;
  node->ai_socktype = type;
  node->ai_protocol = protocol;
  node->ai_addrlen = sizeof(*socket_address);
  node->ai_addr = (struct sockaddr *)socket_address;
  if (canonical) {
    node->ai_canonname = strdup(canonical);
    if (!node->ai_canonname) { ns33_freeaddrinfo(node); return EAI_MEMORY; }
  }
  **tail = node;
  *tail = &node->ai_next;
  return 0;
}

static int resolver_error(void)
{
  switch (h_errno) {
    case HOST_NOT_FOUND: case NO_DATA: return EAI_NONAME;
    case TRY_AGAIN: return EAI_AGAIN;
    default: return EAI_FAIL;
  }
}

int ns33_getaddrinfo(const char *host, const char *service,
                     const struct addrinfo *hints, struct addrinfo **result)
{
  int flags = hints ? hints->ai_flags : 0;
  int type = hints ? hints->ai_socktype : 0;
  int protocol = hints ? hints->ai_protocol : 0;
  int types[2], protocols[2], count = 0, error = 0, numeric_service = 0;
  unsigned ports[2] = {0,0}, port = 0;
  struct addrinfo **tail;
  struct in_addr numeric_host = {0};
  struct hostent *entry = 0;
  int i, address_count = 1;
  const char *canonical = 0;
  if (!result) return EAI_FAIL;
  *result = 0;
  tail = result;
  if (flags & ~(AI_PASSIVE|AI_CANONNAME|AI_NUMERICHOST|AI_NUMERICSERV|AI_ADDRCONFIG)) return EAI_BADFLAGS;
  if (hints && hints->ai_family != AF_UNSPEC && hints->ai_family != AF_INET) return EAI_FAMILY;
  if (type && type != SOCK_STREAM && type != SOCK_DGRAM) return EAI_SOCKTYPE;
  if (protocol && protocol != IPPROTO_TCP && protocol != IPPROTO_UDP) return EAI_SERVICE;
  if ((type == SOCK_STREAM && protocol == IPPROTO_UDP) || (type == SOCK_DGRAM && protocol == IPPROTO_TCP)) return EAI_SERVICE;
  if (!host && !service) return EAI_NONAME;
  if (!host && (flags & AI_CANONNAME)) return EAI_BADFLAGS;
  if (flags & AI_ADDRCONFIG) {
    int configured = ipv4_configured();
    if (configured < 0) return EAI_SYSTEM;
    if (!configured) return EAI_NONAME;
  }
  if (service) {
    const unsigned char *p = (const unsigned char *)service;
    numeric_service = *p != 0;
    for (; *p; ++p) if (*p < '0' || *p > '9') { numeric_service = 0; break; }
    if (!numeric_service && (flags & AI_NUMERICSERV)) return EAI_NONAME;
    if (numeric_service) {
      for (p = (const unsigned char *)service; *p; ++p) {
        port = port * 10 + *p - '0';
        if (port > 65535) return EAI_SERVICE;
      }
    }
  }
  pthread_mutex_lock(&resolver_lock);
  for (i = 0; i < 2; ++i) {
    int candidate_type = i ? SOCK_DGRAM : SOCK_STREAM;
    int candidate_protocol = i ? IPPROTO_UDP : IPPROTO_TCP;
    struct servent *entry;
    if ((type && type != candidate_type) || (protocol && protocol != candidate_protocol)) continue;
    if (service && !numeric_service) {
      entry = getservbyname((char *)service,i ? "udp" : "tcp");
      if (!entry) continue;
      ports[count] = entry->s_port;
    } else ports[count] = htons(port);
    types[count] = candidate_type;
    protocols[count++] = candidate_protocol;
  }
  if (!count) { error = EAI_SERVICE; goto done; }
  if (!host) numeric_host.s_addr = htonl((flags & AI_PASSIVE) ? INADDR_ANY : INADDR_LOOPBACK);
  else if (inet_pton(AF_INET,host,&numeric_host) == 1) {
    if (flags & AI_CANONNAME) canonical = host;
  } else {
    if (!*host || (flags & AI_NUMERICHOST)) { error = EAI_NONAME; goto done; }
    entry = gethostbyname((char *)host);
    if (!entry) { error = resolver_error(); goto done; }
    if (entry->h_addrtype != AF_INET || entry->h_length != 4) { error = EAI_FAMILY; goto done; }
    for (address_count = 0; entry->h_addr_list[address_count]; ++address_count) {}
    if (!address_count) { error = EAI_NONAME; goto done; }
    if (flags & AI_CANONNAME) canonical = entry->h_name;
  }
  for (i = 0; i < address_count; ++i) {
    in_addr_t address = numeric_host.s_addr;
    int j;
    if (entry) memcpy(&address,entry->h_addr_list[i],4);
    for (j = 0; j < count; ++j) {
      error = append_address(&tail,address,ports[j],types[j],protocols[j],flags,canonical);
      if (error) goto done;
      canonical = 0;
    }
  }
done:
  pthread_mutex_unlock(&resolver_lock);
  if (error) { ns33_freeaddrinfo(*result); *result = 0; }
  return error;
}

int ns33_getnameinfo(const struct sockaddr *address, socklen_t address_length,
                     char *host, socklen_t host_length,
                     char *service, socklen_t service_length, int flags)
{
  const struct sockaddr_in *ipv4 = (const struct sockaddr_in *)address;
  struct hostent *host_entry;
  struct servent *service_entry;
  char numeric_host[INET_ADDRSTRLEN], numeric_service[6];
  const char *host_name = 0, *service_name = 0;
  char *owned_host = 0;
  int error = 0;
  if (flags & ~(NI_NUMERICHOST|NI_NUMERICSERV|NI_NAMEREQD|NI_DGRAM)) return EAI_BADFLAGS;
  if (host_length < 0 || service_length < 0) return EAI_OVERFLOW;
  if (!address || address_length < (socklen_t)sizeof(*ipv4) || address->sa_family != AF_INET) return EAI_FAMILY;
  if (!host || !host_length) host = 0;
  if (!service || !service_length) service = 0;
  if (!host && !service) return EAI_NONAME;
  pthread_mutex_lock(&resolver_lock);
  if (host) {
    host_entry = (flags & NI_NUMERICHOST) ? 0 : gethostbyaddr((char *)&ipv4->sin_addr,4,AF_INET);
    if (host_entry) {
      owned_host = strdup(host_entry->h_name);
      if (!owned_host) { error = EAI_MEMORY; goto done; }
      host_name = owned_host;
    }
    else if ((flags & NI_NAMEREQD) && !(flags & NI_NUMERICHOST)) { error = EAI_NONAME; goto done; }
    else {
      if (!inet_ntop(AF_INET,&ipv4->sin_addr,numeric_host,sizeof(numeric_host))) { error = EAI_FAIL; goto done; }
      host_name = numeric_host;
    }
  }
  if (service) {
    service_entry = (flags & NI_NUMERICSERV) ? 0 : getservbyport(ipv4->sin_port,(flags & NI_DGRAM) ? "udp" : "tcp");
    if (service_entry) service_name = service_entry->s_name;
    else { snprintf(numeric_service,sizeof(numeric_service),"%u",ntohs(ipv4->sin_port)); service_name = numeric_service; }
  }
  if ((host && strlen(host_name) >= (size_t)host_length) ||
      (service && strlen(service_name) >= (size_t)service_length)) { error = EAI_OVERFLOW; goto done; }
  if (host) strcpy(host,host_name);
  if (service) strcpy(service,service_name);
done:
  free(owned_host);
  pthread_mutex_unlock(&resolver_lock);
  return error;
}

const char *ns33_gai_strerror(int error)
{
  switch (error) {
    case 0: return "Success";
    case EAI_BADFLAGS: return "Invalid resolver flags";
    case EAI_NONAME: return "Name or service not known";
    case EAI_AGAIN: return "Temporary name resolution failure";
    case EAI_FAIL: return "Name resolution failure";
    case EAI_FAMILY: return "Address family unsupported";
    case EAI_SOCKTYPE: return "Socket type unsupported";
    case EAI_SERVICE: return "Service or protocol unsupported";
    case EAI_MEMORY: return "Memory allocation failure";
    case EAI_SYSTEM: return "System error";
    case EAI_OVERFLOW: return "Result buffer too small";
    default: return "Unknown resolver error";
  }
}
