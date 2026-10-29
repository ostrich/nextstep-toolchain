/* Experimental waitpid over native wait4; interruption contract unresolved.
   This test candidate is not part of the installed compatibility component.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>

struct rusage;
extern pid_t ns33_native_wait4(pid_t, int *, int, struct rusage *) __asm__("_wait4");

pid_t waitpid(pid_t pid, int *status, int options)
{
    int native_status;
    pid_t result;
    if (options & ~(WNOHANG | WUNTRACED)) {
        errno = EINVAL;
        return -1;
    }
    /* Native zero selects any child, not the caller's process group.
       No native process-group selection is available through this syscall. */
    if (pid == 0 || pid < -1) {
        errno = ENOTSUP;
        return -1;
    }
    result = ns33_native_wait4(pid == -1 ? 0 : pid, &native_status, options, 0);
    /* Old kernels may copy an uninitialized status on WNOHANG's zero return.
       Never expose it or change the caller's status unless a child was found. */
    if (result > 0 && status)
        *status = native_status;
    return result;
}
