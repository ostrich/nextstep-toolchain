/* Bridge the musl scanner to native NeXT streams and bounded C strings.
   SPDX-License-Identifier: 0BSD */
#include <string.h>
#include "scan-support.h"

int ns33_scan_read(struct ns33_scan_stream *stream)
{
  int c;
  if (!stream->native || (c = getc(stream->native)) == EOF) return EOF;
  stream->buf[0] = (unsigned char)c;
  stream->rpos = stream->rend = stream->buf + 1;
  return (unsigned char)c;
}

int ns33_vfscanf(FILE *file, const char *format, va_list args)
{
  struct ns33_scan_stream stream = {0};
  va_list copy;
  int result;
  stream.native = file;
  stream.buf = stream.rpos = stream.rend = stream.scratch + 1;
  va_copy(copy, args);
  result = ns33_scan_core(&stream, format, copy);
  va_end(copy);
  if (stream.rpos < stream.rend && ungetc(*stream.rpos, file) == EOF) return EOF;
  return result;
}
int ns33_vsscanf(const char *text, const char *format, va_list args)
{
  struct ns33_scan_stream stream = {0};
  va_list copy;
  int result;
  stream.buf = stream.rpos = (unsigned char *)text;
  stream.rend = stream.rpos + strlen(text);
  va_copy(copy, args);
  result = ns33_scan_core(&stream, format, copy);
  va_end(copy);
  return result;
}
int ns33_sscanf(const char *text, const char *format, ...)
{
  int result;
  va_list args;
  va_start(args, format);
  result = ns33_vsscanf(text, format, args);
  va_end(args);
  return result;
}
int ns33_fscanf(FILE *file, const char *format, ...)
{
  int result;
  va_list args;
  va_start(args, format);
  result = ns33_vfscanf(file, format, args);
  va_end(args);
  return result;
}
int ns33_vscanf(const char *format, va_list args)
{
  return ns33_vfscanf(stdin, format, args);
}
int ns33_scanf(const char *format, ...)
{
  int result;
  va_list args;
  va_start(args, format);
  result = ns33_vfscanf(stdin, format, args);
  va_end(args);
  return result;
}
