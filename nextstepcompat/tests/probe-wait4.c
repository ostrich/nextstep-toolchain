/* Observe native wait4 selectors without assuming modern BSD semantics.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <signal.h>

extern int syscall(int, ...);

static void observe(const char *name, int selector)
{
    int status = 0x1234, result, error;
    errno = 0;
    result = syscall(7, selector, &status, WNOHANG, 0);
    error = errno;
    printf("SELECTOR %s result=%d errno=%d status=%x\n", name, result, error, status);
}
int main(void)
{
    int ready[2], release[2], status, result;
    pid_t child;
    char byte;
    if (pipe(ready) || pipe(release)) return 2;
    child = fork();
    if (child < 0) return 3;
    if (child == 0) {
        close(ready[0]); close(release[1]);
        byte = setpgrp(0, getpid()) == 0 ? 'Y' : 'N';
        if (write(ready[1], &byte, 1) != 1) _exit(4);
        close(ready[1]);
        if (read(release[0], &byte, 1) != 1) _exit(5);
        _exit(23);
    }
    close(ready[1]); close(release[0]);
    if (read(ready[0], &byte, 1) != 1 || byte != 'Y') {
        kill(child, SIGKILL); syscall(7, child, &status, 0, 0); return 6;
    }
    close(ready[0]);
    observe("positive", child);
    observe("any-minus-one", -1);
    observe("own-group-zero", 0);
    observe("child-group-negative", -child);
    byte = 'X';
    if (write(release[1], &byte, 1) != 1) return 7;
    close(release[1]);
    result = syscall(7, child, &status, 0, 0);
    if (result != child || !WIFEXITED(status) || WEXITSTATUS(status) != 23) return 8;
    printf("PASS native wait4 positive PID and exit status; selectors observed\n");
    return 0;
}
