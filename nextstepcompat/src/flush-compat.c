/* C fflush(NULL) over the native libc stream walker. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <pthread.h>
#include <errno.h>

extern int native_fflush(FILE *) __asm__("_fflush");
/* The native callback walker includes dynamically allocated FILE entries.
   Its unspecified integer return value is deliberately ignored. */
extern void native_fwalk(int (*)(FILE *)) __asm__("__fwalk");
static pthread_mutex_t flush_lock = PTHREAD_MUTEX_INITIALIZER;
static int flush_status, flush_errno;

static int flush_output(FILE *file)
{
    if ((file->_flag & _IOWRT) && native_fflush(file) == EOF) {
        flush_status = EOF;
        if (!flush_errno) flush_errno = errno;
    }
    return 0;
}

int ns33_fflush(FILE *file)
{
    int result, saved;
    if (file) return native_fflush(file);
    pthread_mutex_lock(&flush_lock);
    flush_status = flush_errno = 0;
    native_fwalk(flush_output);
    result = flush_status;
    saved = flush_errno;
    pthread_mutex_unlock(&flush_lock);
    if (result == EOF) errno = saved;
    return result;
}
