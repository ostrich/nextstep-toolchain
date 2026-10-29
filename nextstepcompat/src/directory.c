/* The POSIX declaration has no libsys implementation; BSD used a macro.
   SPDX-License-Identifier: 0BSD */
#include <dirent.h>

void ns33_rewinddir(DIR *directory)
{
  seekdir(directory, 0L);
}
