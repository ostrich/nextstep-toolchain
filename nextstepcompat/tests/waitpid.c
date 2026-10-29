/* Supported waitpid semantics and safe rejection of unavailable selectors.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <stdio.h>
#include <errno.h>
#include <limits.h>

extern int syscall(int, ...);
static volatile sig_atomic_t alarm_seen;
static void alarm_handler(int number) { (void)number; alarm_seen = 1; }
static pid_t child = -1;
static pid_t messenger = -1;
static int release_fd = -1;
#define CHECK(test) do { if (!(test)) { printf("FAIL waitpid line %d errno %d\n", __LINE__, errno); goto failed; } } while (0)

static int spawn(void)
{
    int ready[2], release[2];
    char value = 'R';
    if (pipe(ready) || pipe(release)) return -1;
    child = fork();
    if (child < 0) return -1;
    if (child == 0) {
        close(ready[0]); close(release[1]);
        signal(SIGTERM, SIG_DFL); signal(SIGALRM, SIG_DFL);
        alarm(10); /* Bound failures of the parent test itself. */
        if (write(ready[1], &value, 1) != 1) _exit(90);
        close(ready[1]);
        if (read(release[0], &value, 1) != 1) _exit(91);
        _exit(37);
    }
    close(ready[1]); close(release[0]);
    release_fd = release[1];
    if (read(ready[0], &value, 1) != 1) { close(ready[0]); return -1; }
    close(ready[0]);
    return 0;
}
static int release_child(void)
{
    char value = 'X';
    int result = write(release_fd, &value, 1);
    close(release_fd); release_fd = -1;
    return result;
}
int main(void)
{
    int status, result, error;
    pid_t expected;
    struct sigaction action, previous;
    CHECK(spawn() == 0);
    status = 0x1234;
    CHECK(waitpid(child, &status, WNOHANG) == 0 && status == 0x1234);
    CHECK(waitpid(-1, &status, WNOHANG) == 0 && status == 0x1234);
    errno = 0;
    CHECK(waitpid(0, &status, WNOHANG) == -1 && errno == ENOTSUP && status == 0x1234);
    errno = 0;
    CHECK(waitpid(-child, &status, WNOHANG) == -1 && errno == ENOTSUP);
    errno = 0;
    CHECK(waitpid(child, &status, INT_MAX) == -1 && errno == EINVAL);
    errno = 0;
    CHECK(waitpid(getpid(), &status, WNOHANG) == -1 && errno == ECHILD);
    CHECK(kill(child, SIGSTOP) == 0);
    CHECK(waitpid(child, &status, WUNTRACED) == child);
    CHECK(WIFSTOPPED(status) && WSTOPSIG(status) == SIGSTOP);
    CHECK(kill(child, SIGCONT) == 0);
    CHECK(release_child() == 1);
    expected = child;
    result = waitpid(-1, &status, 0);
    if (result == child) child = -1;
    CHECK(result == expected && WIFEXITED(status) && WEXITSTATUS(status) == 37);
    errno = 0;
    CHECK(waitpid(expected, &status, WNOHANG) == -1 && errno == ECHILD);
    CHECK(spawn() == 0);
    expected = child;
    CHECK(release_child() == 1);
    result = waitpid(child, NULL, 0);
    if (result == child) child = -1;
    CHECK(result == expected);
    CHECK(spawn() == 0);
    expected = child;
    CHECK(kill(child, SIGTERM) == 0);
    result = waitpid(child, &status, 0);
    if (result == child) child = -1;
    CHECK(result == expected && WIFSIGNALED(status) && WTERMSIG(status) == SIGTERM);
    CHECK(spawn() == 0);
    action.sa_handler = alarm_handler;
    sigemptyset(&action.sa_mask); action.sa_flags = 0;
    CHECK(sigaction(SIGUSR1, &action, &previous) == 0);
    status = 0x5678;
    messenger = fork();
    CHECK(messenger >= 0);
    if (messenger == 0) {
        sleep(1);
        kill(getppid(), SIGUSR1);
        _exit(0);
    }
    errno = 0;
    result = waitpid(child, &status, 0); error = errno;
    if (result == child) child = -1;
    CHECK(sigaction(SIGUSR1, &previous, NULL) == 0);
    { int sender_status; CHECK(syscall(7, messenger, &sender_status, 0, 0) == messenger); }
    messenger = -1;
    printf("INTERRUPT result=%d errno=%d delivered=%d status=%x\n", result, error, (int)alarm_seen, status);
    CHECK(result == -1 && error == EINTR && alarm_seen && status == 0x5678);
    CHECK(release_child() == 1);
    expected = child;
    result = waitpid(child, &status, 0);
    if (result == child) child = -1;
    CHECK(result == expected && WIFEXITED(status) && WEXITSTATUS(status) == 37);
    puts("PASS waitpid: explicit/any child, status, nonblocking, stop/continue, signal, EINTR and selector limits");
    return 0;
failed:
    if (child > 0) { kill(child, SIGKILL); syscall(7, child, &status, 0, 0); }
    if (messenger > 0) { kill(messenger, SIGKILL); syscall(7, messenger, &status, 0, 0); }
    if (release_fd >= 0) close(release_fd);
    return 1;
}
