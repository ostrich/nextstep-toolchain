/* POSIX environment updates sharing the original libc's environ/getenv.
   Only our own strings/vectors are freed. SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>
#ifdef NS33_SHARED_RUNTIME
/* The fixed-VM system library stores a pointer to the executable's environ.
   Its import archive initializes this bridge before main. A shared library
   cannot resolve the executable-owned environ itself at a fixed address. */
extern char ***ns33_process_environment __asm__("__libsys_environ");
#define environ (*ns33_process_environment)
#else
extern char **environ;
#endif
struct env_string {
  struct env_string *next;
  char text[];
};
static struct env_string *owned_strings;
static char **owned_vector;
static size_t owned_capacity;

static int matches(const char *entry, const char *name, size_t length)
{
  return !strncmp(entry, name, length) && entry[length] == '=';
}

static void collect_strings(void)
{
  struct env_string **link = &owned_strings;
  while (*link) {
    struct env_string *item = *link;
    char **e = environ;
    while (e && *e && *e != item->text) ++e;
    if (e && *e) link = &item->next;
    else { *link = item->next; free(item); }
  }
}

int setenv(const char *name, const char *value, int overwrite)
{
  size_t length, size, count = 0, index;
  struct env_string *item;
  char **vector;
  if (!name || !*name || strchr(name, '=')) { errno = EINVAL; return -1; }
  length = strlen(name);
  index = (size_t)-1;
  if (environ) {
    while (environ[count]) {
      if (index == (size_t)-1 && matches(environ[count], name, length)) index = count;
      ++count;
    }
  }
  if (index != (size_t)-1 && !overwrite) return 0;
  size = strlen(value);
  if (length > (size_t)-1 - sizeof *item - 2 ||
      size > (size_t)-1 - sizeof *item - length - 2) {
    errno = ENOMEM; return -1;
  }
  item = malloc(sizeof *item + length + size + 2);
  if (!item) { errno = ENOMEM; return -1; }
  memcpy(item->text, name, length);
  item->text[length] = '=';
  memcpy(item->text + length + 1, value, size + 1);
  if (index == (size_t)-1) {
    if (count > (size_t)-1 / sizeof(char *) - 2) {
      free(item); errno = ENOMEM; return -1;
    }
    if (environ == owned_vector && count + 2 <= owned_capacity) vector = environ;
    else {
      vector = malloc((count + 2) * sizeof *vector);
      if (!vector) { free(item); errno = ENOMEM; return -1; }
      if (count) memcpy(vector, environ, count * sizeof *vector);
      /* If a caller has replaced environ, its replacement could still refer
         to our previous table. Do not free a table no longer installed. */
      if (environ == owned_vector) free(owned_vector);
      owned_vector = vector;
      owned_capacity = count + 2;
      environ = vector;
    }
    index = count;
    vector[count + 1] = 0;
  }
  environ[index] = item->text;
  item->next = owned_strings;
  owned_strings = item;
  collect_strings();
  return 0;
}

int unsetenv(const char *name)
{
  size_t length;
  char **read, **write;
  if (!name || !*name || strchr(name, '=')) { errno = EINVAL; return -1; }
  length = strlen(name);
  read = write = environ;
  if (read) {
    while (*read) {
      if (!matches(*read, name, length)) *write++ = *read;
      ++read;
    }
    *write = 0;
  }
  collect_strings();
  return 0;
}

/* putenv retains the caller's buffer, unlike setenv. Its mutations must be
   visible through the native getenv and through exec's environment. */
int putenv(char *text)
{
  char *equal;
  char **vector;
  size_t count = 0, index = (size_t)-1, length;
  if (!text || !*text) { errno = EINVAL; return -1; }
  equal = strchr(text, '=');
  if (!equal) return unsetenv(text);
  length = (size_t)(equal - text);
  if (!length) { errno = EINVAL; return -1; }
  if (environ) {
    while (environ[count]) {
      if (index == (size_t)-1 && matches(environ[count], text, length)) index = count;
      ++count;
    }
  }
  if (index == (size_t)-1) {
    if (count > (size_t)-1 / sizeof(char *) - 2) { errno = ENOMEM; return -1; }
    if (environ == owned_vector && count + 2 <= owned_capacity) vector = environ;
    else {
      vector = malloc((count + 2) * sizeof *vector);
      if (!vector) { errno = ENOMEM; return -1; }
      if (count) memcpy(vector, environ, count * sizeof *vector);
      if (environ == owned_vector) free(owned_vector);
      owned_vector = vector;
      owned_capacity = count + 2;
      environ = vector;
    }
    index = count;
    vector[count + 1] = 0;
  }
  environ[index] = text;
  collect_strings();
  return 0;
}
