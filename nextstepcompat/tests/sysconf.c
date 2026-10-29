/* Native SDK queries, errno preservation and inherited descriptor cleanup.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <unistd.h>
#include <limits.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <stdlib.h>

extern int getdtablesize(void);

int main(void)
{
    const int names[] = {_SC_ARG_MAX, _SC_CHILD_MAX, _SC_CLK_TCK,
        _SC_JOB_CONTROL, _SC_NGROUPS_MAX, _SC_OPEN_MAX, _SC_SAVED_IDS,
        _SC_STREAM_MAX, _SC_TZNAME_MAX, _SC_VERSION};
    long expected[] = {ARG_MAX, CHILD_MAX, CLK_TCK, _POSIX_JOB_CONTROL,
        NGROUPS_MAX, getdtablesize(), _POSIX_SAVED_IDS, STREAM_MAX,
        TZNAME_MAX, _POSIX_VERSION};
    int i, fd, high, status;
    pid_t child;
    for (i = 0; i < 10; ++i) {
        errno = EDOM;
        if (sysconf(names[i]) != expected[i] || errno != EDOM) {
            printf("FAIL sysconf selector %d\n", names[i]);
            return 1;
        }
    }
    errno = 0;
    if (sysconf(-1) != -1 || errno != EINVAL)
        return 2;
    errno = 0;
    if (sysconf(INT_MAX) != -1 || errno != EINVAL)
        return 3;
    fd = open("/dev/null", O_RDONLY);
    if (fd < 0 || fd >= sysconf(_SC_OPEN_MAX))
        return 4;
    high = (int)sysconf(_SC_OPEN_MAX) - 1;
    if (high <= 3 || dup2(fd, high) != high)
        return 5;
    child = fork();
    if (child < 0)
        return 6;
    if (child == 0) {
        for (i = (int)sysconf(_SC_OPEN_MAX); i > 3;)
            close(--i);
        errno = 0;
        _exit(fcntl(high, F_GETFD) == -1 && errno == EBADF ? 0 : 7);
    }
    if (wait(&status) != child || !WIFEXITED(status) || WEXITSTATUS(status))
        return 8;
    if (fcntl(high, F_GETFD) < 0 || close(high) || close(fd))
        return 9;
    puts("PASS sysconf: ten SDK selectors, invalid selectors, errno and descriptor bounds");
    return 0;
}
