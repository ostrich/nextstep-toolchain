/* Runtime queries for the selectors published by the NEXTSTEP SDK.
   SPDX-License-Identifier: 0BSD */
#include <unistd.h>
#include <limits.h>
#include <time.h>
#include <errno.h>

extern int getdtablesize(void);

long sysconf(int name)
{
    switch (name) {
    case _SC_ARG_MAX:
        return ARG_MAX;
    case _SC_CHILD_MAX:
        return CHILD_MAX;
    case _SC_CLK_TCK:
        return CLK_TCK;
    case _SC_JOB_CONTROL:
        return _POSIX_JOB_CONTROL;
    case _SC_NGROUPS_MAX:
        return NGROUPS_MAX;
    case _SC_OPEN_MAX:
        /* Use the native process limit, not the SDK's compile-time ceiling. */
        return getdtablesize();
    case _SC_SAVED_IDS:
        return _POSIX_SAVED_IDS;
    case _SC_STREAM_MAX:
        return STREAM_MAX;
    case _SC_TZNAME_MAX:
        return TZNAME_MAX;
    case _SC_VERSION:
        return _POSIX_VERSION;
    default:
        errno = EINVAL;
        return -1;
    }
}
