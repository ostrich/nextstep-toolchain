/* NEXTSTEP provides only C/POSIX locale collation.
   SPDX-License-Identifier: 0BSD */
#include <string.h>
#include <errno.h>

int ns33_strcoll(const char *left, const char *right)
{
  return strcmp(left, right);
}

size_t ns33_strxfrm(char *destination, const char *source, size_t size)
{
  size_t length = strlen(source);
  /* The standard leaves destination unspecified for insufficient space.
     The returned length excludes NUL even when size is zero. */
  if (length < size)
    memcpy(destination, source, length + 1);
  return length;
}

char *ns33_strerror(int error)
{
  static char illegal_sequence[] = "Invalid or incomplete multibyte sequence";
  static char no_message[] = "No message of desired type";
  static char overflow[] = "Value too large for defined data type";
  static char unknown[] = "Unknown error";
  if (error == EILSEQ)
    return illegal_sequence;
  if (error == ENOMSG)
    return no_message;
  /* The original implementation indexes its error array with negative inputs. */
  if (error == EOVERFLOW)
    return overflow;
  if (error < 0)
    return unknown;
  return ns33_native_strerror(error);
}

int ns33_strerror_r(int error, char *buffer, size_t size)
{
  const char *message = ns33_strerror(error);
  size_t length = strlen(message);
  size_t count;
  if (size == 0)
    return ERANGE;
  count = length < size ? length : size - 1;
  memcpy(buffer, message, count);
  buffer[count] = 0;
  if (length >= size)
    return ERANGE;
  return (error < 0 || (error > 87 && error != EILSEQ && error != ENOMSG && error != EOVERFLOW))
    ? EINVAL : 0;
}
