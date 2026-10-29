/* C90 byte-string boundaries and overlap, independent of BSD extensions.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <string.h>
static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
  fprintf(stderr, "memory line %d: %s\n", __LINE__, #x); } } while (0)
int main(void)
{
  unsigned char a[160], expected[160], source[160];
  unsigned i, j, n, offset;
  char text[64], *token;
  for (i = 0; i < sizeof source; ++i) source[i] = (unsigned char)(i * 37);
  for (offset = 0; offset < 8; ++offset) {
    for (n = 0; n <= 64; ++n) {
      memset(a, 0xa5, sizeof a);
      CHECK(memcpy(a + offset, source + offset, n) == a + offset);
      for (i = 0; i < sizeof a; ++i)
        CHECK(a[i] == (i >= offset && i < offset + n ? source[i] : 0xa5));
      CHECK(memcmp(a + offset, source + offset, n) == 0);
      for (j = 0; j < 8; ++j) {
        memcpy(a, source, sizeof a);
        memcpy(expected, source, sizeof a);
        for (i = 0; i < n; ++i) expected[offset + j + i] = source[offset + i];
        CHECK(memmove(a + offset + j, a + offset, n) == a + offset + j);
        CHECK(memcmp(a, expected, sizeof a) == 0);
        memcpy(a, source, sizeof a);
        memcpy(expected, source, sizeof a);
        for (i = 0; i < n; ++i) expected[offset + i] = source[offset + j + i];
        CHECK(memmove(a + offset, a + offset + j, n) == a + offset);
        CHECK(memcmp(a, expected, sizeof a) == 0);
      }
    }
  }
  for (i = 0; i < 256; ++i) {
    memset(a, 0, sizeof a);
    a[79] = (unsigned char)i;
    CHECK(memchr(a, i, 79) == (i ? 0 : a));
    CHECK(memchr(a, i, 80) == (i ? a + 79 : a));
    CHECK(memchr(a, i, 0) == 0);
    if (i) {
      text[0] = 'a'; text[1] = (char)i; text[2] = 0;
      CHECK(strchr(text, i) == (i == 'a' ? text : text + 1));
      CHECK(strrchr(text, i) == text + 1);
    }
  }
  CHECK(memcmp("\200", "\177", 1) > 0);
  CHECK(strcmp("\200", "\177") > 0);
  CHECK(strncmp("\200", "\177", 1) > 0);
  CHECK(strncmp("a", "z", 0) == 0);
  { const char *word = "abc"; CHECK(strchr(word, 0) == word + 3); }
  strcpy(text, ",,one::two,three,,");
  token = strtok(text, ",:"); CHECK(token && !strcmp(token, "one"));
  token = strtok(0, ":,"); CHECK(token && !strcmp(token, "two"));
  token = strtok(0, ","); CHECK(token && !strcmp(token, "three"));
  CHECK(strtok(0, ",") == 0);
  strcpy(text, "abc");
  CHECK(strncat(text, "xyz", 0) == text && !strcmp(text, "abc"));
  CHECK(strcat(text, "xyz") == text && !strcmp(text, "abcxyz"));
  CHECK(strlen(text) == 6);
  printf("memory boundaries: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
