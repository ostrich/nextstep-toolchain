/* Rewind after EOF and across multiple native directory buffers.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

int main(void)
{
  char temporary[128];
  char path[256], names[50][256], base[129];
  DIR *directory;
  struct dirent *entry;
  int i, fd, count = 0, failed = 0;
  alarm(30);
  snprintf(temporary, sizeof(temporary), "/tmp/ns33-rewind-%ld", (long)getpid());
  if (mkdir(temporary, 0700)) return 2;
  memset(base, 'x', 128); base[128] = 0;
  for (i = 0; i < 48; i++) {
    snprintf(path, sizeof(path), "%s/%s%02d", temporary, base, i);
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) return 3;
    if (close(fd)) return 4;
  }
  directory = opendir(temporary);
  if (!directory) return 5;
  while ((entry = readdir(directory))) {
    if (count == 50) return 6;
    strcpy(names[count++], entry->d_name);
  }
  if (count != 50) failed = 1;
  rewinddir(directory);
  for (i = 0; i < count; i++) {
    entry = readdir(directory);
    if (!entry || strcmp(entry->d_name, names[i])) failed = 1;
  }
  if (readdir(directory)) failed = 1;
  rewinddir(directory);
  entry = readdir(directory);
  if (!entry || strcmp(entry->d_name, names[0])) failed = 1;
  if (closedir(directory)) failed = 1;
  for (i = 0; i < 48; i++) {
    snprintf(path, sizeof(path), "%s/%s%02d", temporary, base, i);
    if (unlink(path)) failed = 1;
  }
  if (rmdir(temporary)) failed = 1;
  printf("rewinddir adapter: %s\n", failed ? "FAIL" : "PASS");
  return failed;
}
