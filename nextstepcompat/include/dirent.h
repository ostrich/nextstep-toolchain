/* Native readdir returns the BSD layout, not the SDK's POSIX d_off layout.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_DIRENT_H
#define NEXTSTEPCOMPAT_DIRENT_H
#include <sys/types.h>
/* Use the public POSIX tag with the actual BSD readdir ABI. A tag macro
   breaks clients that forward-declare struct dirent before this header. */
struct dirent {
  unsigned long d_fileno;
  unsigned short d_reclen;
  unsigned short d_namlen;
  char d_name[256];
};
#include <sys/dir.h>
#ifdef __cplusplus
extern "C" {
#endif
int dirfd(DIR *);
#ifdef rewinddir
#undef rewinddir
#endif
void rewinddir(DIR *) __asm__("_ns33_rewinddir");
#ifdef __cplusplus
}
#endif
#endif
