/* Bridge the native BSD int array to the SDK's POSIX gid_t array.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/param.h>
#include <unistd.h>
#include <errno.h>

extern int ns33_native_getgroups(int, int *) __asm__("_getgroups");

int ns33_getgroups(int size, gid_t *groups)
{
    int native[NGROUPS], count, i;
    if (size < 0) {
        errno = EINVAL;
        return -1;
    }
    /* The BSD call has no count-only query. A full native array also avoids
       giving the kernel the smaller POSIX element size from the SDK. */
    count = ns33_native_getgroups(NGROUPS, native);
    if (count < 0)
        return -1;
    if (size == 0)
        return count;
    if (size < count) {
        errno = EINVAL;
        return -1;
    }
    if (count && !groups) {
        errno = EFAULT;
        return -1;
    }
    for (i = 0; i < count; ++i)
        groups[i] = (gid_t)native[i];
    return count;
}

extern int ns33_native_setgroups(int, const int *) __asm__("_setgroups");

int ns33_setgroups(int count, const gid_t *groups)
{
    int native[NGROUPS], i;
    if (count < 0 || count > NGROUPS) { errno = EINVAL; return -1; }
    if (count && !groups) { errno = EFAULT; return -1; }
    for (i = 0; i < count; ++i) native[i] = groups[i];
    return ns33_native_setgroups(count, native);
}

/* The native BSD entry takes a PID; POSIX getpgrp has no arguments. */
extern pid_t ns33_native_getpgrp(pid_t) __asm__("_getpgrp");
pid_t ns33_getpgrp(void)
{
    return ns33_native_getpgrp(0);
}

/* BSD setpgrp uses a literal group zero; POSIX setpgid uses the process PID. */
extern int ns33_native_setpgrp(int, int) __asm__("_setpgrp");
int setpgid(pid_t pid, pid_t group)
{
    if (pid < 0 || group < 0) { errno = EINVAL; return -1; }
    if (!group) group = pid ? pid : getpid();
    return ns33_native_setpgrp(pid, group);
}
