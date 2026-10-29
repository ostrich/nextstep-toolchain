/* Imported POSIX implementations expect malloc failure to set errno.
   Native NeXT malloc can return NULL with errno unchanged.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <errno.h>
void *ns33_compat_malloc(size_t size)
{
  void *result = malloc(size);
  if (!result) errno = ENOMEM;
  return result;
}
