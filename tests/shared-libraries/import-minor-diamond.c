/* Shared imports that require old and new exports of a common dependency.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <wchar.h>
#include <math.h>
extern void *libiconv_open(const char *, const char *);
extern int libiconv_close(void *);
extern unsigned lzo_version(void);
size_t (*volatile old_api)(wchar_t *, const char *, size_t, mbstate_t *) = mbrtowc;
static double (*volatile new_api)(double) = trunc;
int main(void)
{
  void *converter = libiconv_open("UTF-8", "ISO-8859-1");
  void *allocation = malloc(16);
  if (converter == (void *)-1 || !allocation || !old_api) return 2;
  {
    mbstate_t state = {0};
    wchar_t value;
    if(old_api(&value, "A", 1, &state) != 1 || value != L'A') return 3;
  }
  libiconv_close(converter);
  free(allocation);
  return lzo_version() < 0x2000 || new_api(1.5) != 1.0;
}
