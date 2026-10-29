/* Checked front ends for the native 30-bit zone allocator.
   Returned pointers retain native malloc_size/free compatibility.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* Explicit bindings avoid recursing through the public header aliases.
   Tests substitute the native operations before including this file. */
#ifndef NS33_NATIVE_MALLOC
extern void *ns33_native_malloc(size_t) __asm__("_malloc");
extern size_t ns33_native_malloc_size(void *) __asm__("_malloc_size");
extern void ns33_native_free(void *) __asm__("_free");
extern size_t ns33_native_vm_page_size __asm__("_vm_page_size");
#define NS33_NATIVE_MALLOC ns33_native_malloc
#define NS33_NATIVE_SIZE ns33_native_malloc_size
#define NS33_NATIVE_FREE ns33_native_free
#define NS33_NATIVE_PAGESIZE() (ns33_native_vm_page_size)
#endif

static int representable(size_t size)
{
  int page = NS33_NATIVE_PAGESIZE();
  const size_t header_max = 0x3fffffffUL;
  /* Worst alignment among NIHS is eight bytes. nxzonemalloc adds a
     four-byte header and up to seven alignment bytes. moremem adds a
     12-byte dummy and eight-byte deadwood. VM rounding adds page-1;
     joining adjacent regions can add another eight bytes to a header.
     Keep their sum representable before calling the native allocator.
     This bounds the default external zone, not arbitrary nested zones. */
  const size_t overhead = 4 + 7 + 12 + 8 + 8;
  if (page <= 0 || (size_t)page > header_max - overhead ||
      size > header_max - overhead - ((size_t)page - 1)) {
    errno = ENOMEM;
    return 0;
  }
  return 1;
}

void *ns33_malloc(size_t size)
{
  void *result;
  if (!representable(size)) return 0;
  result = NS33_NATIVE_MALLOC(size);
  if (!result) errno = ENOMEM;
  return result;
}

void *ns33_calloc(size_t count, size_t size)
{
  void *result;
  if (size && count > (size_t)-1 / size) {
    errno = ENOMEM;
    return 0;
  }
  size *= count;
  result = ns33_malloc(size);
  if (result && size) memset(result, 0, size);
  return result;
}

void *ns33_realloc(void *old, size_t size)
{
  size_t previous;
  void *result;
  /* Native realloc copies to NULL on some allocation-failure paths.
     Allocate first, retaining the old object on any failure. Native
     malloc_size also handles native page-aligned allocations. */
  if (!representable(size)) return 0;
  previous = old ? NS33_NATIVE_SIZE(old) : 0;
  if (old && size && size <= previous) return old;
  result = ns33_malloc(size);
  if (!result) return 0;
  if (old) {
    if (previous > size) previous = size;
    if (previous) memcpy(result, old, previous);
    NS33_NATIVE_FREE(old);
  }
  return result;
}
