/* Exercise declarations against the real system libraries. SPDX-License-Identifier: 0BSD */
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static volatile sig_atomic_t delivered;
static int checks;
static void handler(int number)
{
    if (number == SIGUSR1)
        delivered++;
}
#define CHECK(expression) do { \
    checks++; \
    if (!(expression)) { \
        fprintf(stderr, "sdk headers: failed line %d: %s\n", __LINE__, #expression); \
        return 1; \
    } \
} while (0)

int main(void)
{
    char path[128];
    char bytes[8];
    struct stat st;
    void (*previous)(int);
    int fd, pipes[2], saved;
    snprintf(path, sizeof(path), "/private/tmp/sdk-header-%ld", (long)getpid());
    fd = open(path, O_CREAT | O_EXCL | O_RDWR, (mode_t)0600);
    CHECK(fd >= 0);
    /* Remove the directory entry immediately, including on later failure. */
    CHECK(unlink(path) == 0);
    CHECK(write(fd, "header", (size_t)6) == 6);
    CHECK(fstat(fd, &st) == 0);
    CHECK(S_ISREG(st.st_mode));
    CHECK((st.st_mode & 0777) == 0600);
    CHECK(st.st_size == 6);
    CHECK(st.st_uid == getuid());
    CHECK(lseek(fd, (off_t)0, SEEK_SET) == 0);
    CHECK(read(fd, bytes, (size_t)6) == 6);
    CHECK(memcmp(bytes, "header", (size_t)6) == 0);
    CHECK(fcntl(fd, F_SETFD, FD_CLOEXEC) == 0);
    CHECK((fcntl(fd, F_GETFD) & FD_CLOEXEC) != 0);
    CHECK(close(fd) == 0);
    CHECK(pipe(pipes) == 0);
    CHECK(write(pipes[1], "pipe", (size_t)4) == 4);
    CHECK(read(pipes[0], bytes, (size_t)4) == 4);
    CHECK(memcmp(bytes, "pipe", (size_t)4) == 0);
    CHECK(close(pipes[0]) == 0);
    CHECK(close(pipes[1]) == 0);
    /* The SDK also declares POSIX signal interfaces absent from libsys_s.a.
       Exercise the available BSD implementation, without inventing stubs. */
    previous = signal(SIGUSR1, handler);
    CHECK(previous != BADSIG);
    saved = sigblock(sigmask(SIGUSR1));
    CHECK(saved >= 0);
    CHECK(raise(SIGUSR1) == 0);
    CHECK(delivered == 0);
    CHECK(sigsetmask(saved) >= 0);
    CHECK(delivered == 1);
    CHECK(signal(SIGUSR1, previous) != BADSIG);
    printf("sdk headers: %d checks passed\n", checks);
    return 0;
}
