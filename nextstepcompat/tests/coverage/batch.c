/* Bounded isolation for independently linked libc-test executables.
 * SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include "batch-names.h"
int main(int argc, char **argv)
{
    unsigned i, failures = 0;
    char directory[1024], *slash;
    struct rlimit limit;
    if (strlen(argv[0]) >= sizeof directory) return 2;
    strcpy(directory, argv[0]);
    slash = strrchr(directory, '/');
    if (slash) { *slash = 0; if (chdir(*directory ? directory : "/")) return 2; }
    limit.rlim_cur = limit.rlim_max = 0;
    if (setrlimit(RLIMIT_CORE, &limit)) return 2;
    puts("API BEGIN"); fflush(stdout);
    for (i = 0; names[i]; ++i) {
        char path[256];
        int pid, got, status;
        if (strlen(names[i]) + 3 > sizeof path) return 2;
        strcpy(path, "./"); strcat(path, names[i]);
        printf("API RUN %s\n", names[i]); fflush(stdout);
        pid = fork();
        if (!pid) {
            signal(SIGALRM, SIG_DFL); alarm(20);
            execl(path, path, test_args[i][0], test_args[i][1], (char *)0); _exit(127);
        }
        if (pid < 0) return 2;
        do { got = wait(&status); } while ((got < 0 && errno == EINTR) || (got > 0 && got != pid));
        if (got != pid) return 2;
        printf("API RESULT %s exit %d signal %d\n", names[i],
               WIFEXITED(status) ? WEXITSTATUS(status) : -1,
               WIFSIGNALED(status) ? WTERMSIG(status) : 0);
        failures += !WIFEXITED(status) || WEXITSTATUS(status) != 0;
        fflush(stdout);
    }
    printf("API END %u tests %u failures\n", i, failures);
    return failures != 0;
}
