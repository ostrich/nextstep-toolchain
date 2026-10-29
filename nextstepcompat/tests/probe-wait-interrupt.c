/* Compare native wait3/wait4 signal interruption without imposing POSIX claims.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>

struct rusage;
extern pid_t native_wait4(pid_t, int *, int, struct rusage *) __asm__("_wait4");
static volatile sig_atomic_t delivered;
static void caught(int number) { (void)number; delivered = 1; }
static int profile(int use_wait3, int restart)
{
    struct sigaction action, previous;
    pid_t child, result;
    int status = 0x1234, error;
    memset(&action, 0, sizeof(action));
    action.sa_handler = caught;
    action.sa_flags = restart ? SA_RESTART : 0;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGUSR1, &action, &previous)) return 2;
    delivered = 0;
    child = fork();
    if (child < 0) return 3;
    if (child == 0) {
        sleep(1); kill(getppid(), SIGUSR1); sleep(1); _exit(23);
    }
    errno = 0;
    result = use_wait3 ? wait3(&status, 0, NULL) : native_wait4(child, &status, 0, NULL);
    error = errno;
    printf("NATIVE %s restart=%d result=%s errno=%d delivered=%d status=%x\n",
           use_wait3 ? "wait3" : "wait4", restart,
           result == child ? "child" : result == -1 ? "error" : "other",
           error, (int)delivered, status);
    if (result == -1 && error == EINTR) {
        do { result = native_wait4(child, &status, 0, NULL); } while (result < 0 && errno == EINTR);
    }
    sigaction(SIGUSR1, &previous, NULL);
    if (result != child || !delivered || !WIFEXITED(status) || WEXITSTATUS(status) != 23)
        return 4;
    return 0;
}
int main(void)
{
    if (profile(0,0) || profile(0,1) || profile(1,0) || profile(1,1)) return 1;
    puts("PASS native wait interruption profiles collected");
    return 0;
}
