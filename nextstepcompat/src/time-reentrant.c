/* POSIX result-buffer adapters over the native timezone implementation.
   Native non-reentrant callers retain their original thread-safety limits.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
#include <pthread.h>
#include <errno.h>
static pthread_mutex_t conversion_lock = PTHREAD_MUTEX_INITIALIZER;
static struct tm *convert(const time_t *value, struct tm *result, int local)
{
  struct tm *native;
  if (!value || !result) { errno = EINVAL; return 0; }
  pthread_mutex_lock(&conversion_lock);
  native = local ? localtime(value) : gmtime(value);
  if (native) *result = *native;
  pthread_mutex_unlock(&conversion_lock);
  return native ? result : 0;
}
struct tm *ns33_localtime_r(const time_t *value, struct tm *result)
{ return convert(value, result, 1); }
struct tm *ns33_gmtime_r(const time_t *value, struct tm *result)
{ return convert(value, result, 0); }
