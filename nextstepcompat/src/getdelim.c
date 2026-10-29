/* POSIX line input over native buffered NeXT streams.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
static ssize_t input_error(FILE *file, int error)
{
  file->_flag |= _IOERR;
  errno = error;
  return -1;
}

ssize_t getdelim(char **line, size_t *capacity, int delimiter, FILE *file)
{
  size_t length = 0;
  int c;
  if (!line || !capacity) return input_error(file, EINVAL);
  if (!*line) *capacity = 0;
  for (;;) {
    /* Reserve the terminator before consuming input. Preserve the caller's
       allocation and capacity on allocation failure. All supported target
       ssize_t types are signed int, so cap allocation arithmetic at INT_MAX. */
    if (length + 1 >= *capacity) {
      size_t needed, size;
      char *buffer;
      if (length == INT_MAX) return input_error(file, EOVERFLOW);
      needed = length + 2;
      size = *capacity < 128 ? 128 : *capacity;
      if (size < needed) size = size > (size_t)INT_MAX / 2 ? needed : size * 2;
      buffer = realloc(*line, size);
      if (!buffer) return input_error(file, ENOMEM);
      *line = buffer;
      *capacity = size;
    }
    c = getc(file);
    if (c == EOF) {
      (*line)[length] = 0;
      if (ferror(file) || !length) return -1;
      return (ssize_t)length;
    }
    if (length == INT_MAX) {
      ungetc(c, file);
      return input_error(file, EOVERFLOW);
    }
    (*line)[length++] = (char)c;
    (*line)[length] = 0;
    if ((unsigned char)c == (unsigned char)delimiter) return (ssize_t)length;
  }
}

ssize_t getline(char **line, size_t *capacity, FILE *file)
{
  return getdelim(line, capacity, '\n', file);
}
