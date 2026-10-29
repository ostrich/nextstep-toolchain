#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int compare(const void *a, const void *b)
{
  int x = *(const int *)a, y = *(const int *)b;
  return (x > y) - (x < y);
}
int main(void)
{
  static const char text[] = "modern GCC / original SDK";
  char *copy = malloc(sizeof text);
  char buffer[64];
  int values[] = { 9, -4, 3, 2 };
  FILE *file;
  if (!copy) return 1;
  if (sizeof(wchar_t) != 2 || sizeof(L"x"[0]) != sizeof(wchar_t)) return 11;
  memcpy(copy, text, sizeof text);
  if (strcmp(copy, text) || strlen(copy) != sizeof text - 1) return 2;
  qsort(values, 4, sizeof(int), compare);
  if (values[0] != -4 || values[3] != 9) return 3;
  if (strtol("12345", (char **)0, 10) != 12345) return 4;
  file = tmpfile();
  if (!file) return 5;
  if (fwrite(copy, 1, sizeof text, file) != sizeof text) return 6;
  if (fseek(file, 0, SEEK_SET)) return 7;
  if (fread(buffer, 1, sizeof text, file) != sizeof text) return 8;
  if (memcmp(buffer, text, sizeof text)) return 9;
  if (fclose(file)) return 10;
  free(copy);
  printf("libc smoke: passed\n");
  return 0;
}
