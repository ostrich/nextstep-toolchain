/* Modern POSIX predicates over native file mode bits. SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#ifdef __cplusplus
#define REQUIRE(x) static_assert(x, #x)
#else
#define REQUIRE(x) _Static_assert(x, #x)
#endif
REQUIRE(S_ISLNK(S_IFLNK));
REQUIRE(S_ISLNK(S_IFLNK | 07777));
REQUIRE(!S_ISLNK(S_IFREG | 07777));
REQUIRE(!S_ISLNK(S_IFDIR | 07777));
REQUIRE(!S_ISLNK(S_IFSOCK | 07777));
REQUIRE(S_ISSOCK(S_IFSOCK));
REQUIRE(S_ISSOCK(S_IFSOCK | 07777));
REQUIRE(!S_ISSOCK(S_IFREG | 07777));
REQUIRE(!S_ISSOCK(S_IFDIR | 07777));
REQUIRE(!S_ISSOCK(S_IFLNK | 07777));
int main(void)
{
  mode_t link = S_IFLNK, sock = S_IFSOCK;
  if (!S_ISLNK(link++) || link != S_IFLNK + 1) return 1;
  if (!S_ISSOCK(sock++) || sock != S_IFSOCK + 1) return 1;
  puts("PASS file type predicates and single evaluation");
  return 0;
}
