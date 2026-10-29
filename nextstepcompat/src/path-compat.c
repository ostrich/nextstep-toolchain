/* Reentrant path resolution without changing the process working directory.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>
#include <sys/param.h>
#include <sys/stat.h>
#ifdef __NeXT__
extern int readlink(const char *, char *, size_t);
extern int lstat(const char *, struct stat *);
#endif
#ifndef MAXSYMLINKS
#define MAXSYMLINKS 20
#endif

static int same_inode(const struct stat *a, const struct stat *b)
{ return a->st_dev == b->st_dev && a->st_ino == b->st_ino; }

char *getcwd(char *buffer, size_t size)
{
  char parent[MAXPATHLEN] = ".", result[MAXPATHLEN];
  struct stat current, root, above, candidate;
  size_t length = 1, pos = sizeof(result) - 1, needed;
  result[pos] = 0;
  if (buffer && !size) { errno = EINVAL; return 0; }
  if (stat(".", &current) || stat("/", &root)) return 0;
  while (!same_inode(&current, &root)) {
    DIR *directory;
    struct dirent *entry;
    size_t parent_length;
    int found = 0, saved;
    if (length + 3 >= sizeof(parent)) { errno = ENAMETOOLONG; return 0; }
    memcpy(parent + length, "/..", 4); length += 3;
    directory = opendir(parent);
    if (!directory) return 0;
    if (fstat(dirfd(directory), &above)) {
      saved = errno; closedir(directory); errno = saved; return 0;
    }
    if (same_inode(&above, &current)) {
      closedir(directory); errno = ENOENT; return 0;
    }
    parent_length = length;
    errno = 0;
    while ((entry = readdir(directory))) {
      size_t n;
      if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
      if (current.st_dev == above.st_dev && entry->d_ino != current.st_ino) continue;
      n = strlen(entry->d_name);
      if (parent_length + n + 2 > sizeof(parent)) continue;
      parent[parent_length] = '/';
      memcpy(parent + parent_length + 1, entry->d_name, n + 1);
      if (!lstat(parent, &candidate) && same_inode(&candidate, &current)) {
        if (n + 1 > pos) {
          closedir(directory); errno = ERANGE; return 0;
        }
        pos -= n; memcpy(result + pos, entry->d_name, n);
        result[--pos] = '/'; found = 1; break;
      }
      parent[parent_length] = 0;
    }
    saved = errno;
    if (closedir(directory) && found) return 0;
    if (!found) { errno = saved ? saved : ENOENT; return 0; }
    parent[parent_length] = 0;
    current = above;
  }
  if (!result[pos]) result[--pos] = '/';
  needed = sizeof(result) - pos;
  if (size && size < needed) { errno = ERANGE; return 0; }
  if (!buffer) {
    buffer = malloc(size ? size : needed);
    if (!buffer) { errno = ENOMEM; return 0; }
  }
  memcpy(buffer, result + pos, needed);
  return buffer;
}

char *ns33_realpath(const char *path, char *resolved)
{
  char pending[MAXPATHLEN], target[MAXPATHLEN], *cursor, *buffer = resolved;
  unsigned links = 0;
  int saved;
  size_t n;
  if (!path) { errno = EINVAL; return 0; }
  if (!*path) { errno = ENOENT; return 0; }
  for (n = 0; n < sizeof(pending) && path[n]; ++n) {}
  if (n == sizeof(pending)) { errno = ENAMETOOLONG; return 0; }
  memcpy(pending, path, n + 1);
  if (!buffer) {
    buffer = malloc(MAXPATHLEN);
    if (!buffer) { errno = ENOMEM; return 0; }
  }
  if (pending[0] == '/') strcpy(buffer, "/");
  else if (!getcwd(buffer, MAXPATHLEN)) goto fail;
  cursor = pending;
  while (*cursor) {
    char *component;
    size_t length, parent_length;
    struct stat info;
    while (*cursor == '/') ++cursor;
    if (!*cursor) break;
    component = cursor;
    while (*cursor && *cursor != '/') ++cursor;
    length = cursor - component;
    if (length == 1 && component[0] == '.') continue;
    if (length == 2 && component[0] == '.' && component[1] == '.') {
      char *slash = strrchr(buffer, '/');
      if (slash != buffer) *slash = 0;
      else buffer[1] = 0;
      continue;
    }
    parent_length = strlen(buffer);
    n = parent_length;
    if (n > 1) ++n;
    if (n + length >= MAXPATHLEN) { errno = ENAMETOOLONG; goto fail; }
    if (parent_length > 1) buffer[parent_length] = '/';
    memcpy(buffer + n, component, length); buffer[n + length] = 0;
    if (lstat(buffer, &info)) goto fail;
    if ((info.st_mode & S_IFMT) == S_IFLNK) {
      int count;
      if (++links > MAXSYMLINKS) { errno = ELOOP; goto fail; }
      count = readlink(buffer, target, sizeof(target));
      if (count < 0) goto fail;
      if (!count) { errno = ENOENT; goto fail; }
      if ((size_t)count >= sizeof(target) || count + strlen(cursor) >= sizeof(target)) {
        errno = ENAMETOOLONG; goto fail;
      }
      target[count] = 0; strcat(target, cursor);
      if (target[0] == '/') strcpy(buffer, "/");
      else buffer[parent_length] = 0;
      strcpy(pending, target); cursor = pending;
    } else if (*cursor && !S_ISDIR(info.st_mode)) {
      errno = ENOTDIR; goto fail;
    }
  }
  return buffer;
fail:
  saved = errno;
  if (!resolved) free(buffer);
  errno = saved;
  return 0;
}
