/* Append/truncate, seek and descriptor ownership regressions. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
static int failures, checks;
#define CHECK(x) do { checks++; if (!(x)) { failures++; printf("FAIL line %d: %s errno=%d\n", __LINE__, #x, errno); } } while (0)
static void seed(void)
{
    int fd = open("append-test", O_WRONLY|O_CREAT|O_TRUNC, 0600);
    CHECK(fd >= 0);
    if (fd >= 0) { CHECK(write(fd, "old-content", 11) == 11); close(fd); }
}
static void content(const char *expected)
{
    char bytes[128]; int fd = open("append-test", O_RDONLY), n;
    CHECK(fd >= 0);
    if (fd < 0) return;
    n = read(fd, bytes, sizeof(bytes)); close(fd);
    CHECK(n == (int)strlen(expected));
    CHECK(n == (int)strlen(expected) && !memcmp(bytes, expected, n));
}
int main(void)
{
    const char *modes[] = {"a", "ab", "a+", "ab+", "a+b"};
    int i, kind, fd, flags, original_flags = 0, alias; FILE *f; char bytes[8];
    for (i = 0; i < 5; i++) for (kind = 0; kind < 3; kind++) {
        printf("append-case mode=%s kind=%d\n", modes[i], kind);
        seed();
        if (kind == 0) f = fopen("append-test", modes[i]);
        else if (kind == 1) {
            fd = open("append-test", O_RDWR|O_NONBLOCK);
            original_flags = fcntl(fd, F_GETFL, 0);
            CHECK(fd >= 0); f = fdopen(fd, modes[i]);
        } else {
            f = fopen("append-test", "r");
            CHECK(f != NULL);
            if (!f) continue;
            f = freopen("append-test", modes[i], f);
        }
        CHECK(f != NULL); if (!f) continue;
        fd = fileno(f); flags = fcntl(fd, F_GETFL, 0);
        CHECK(flags >= 0 && (flags & O_APPEND));
        if (kind == 1) CHECK((flags & ~O_APPEND) == (original_flags & ~O_APPEND));
        CHECK(ftruncate(fd, 0) == 0);
        CHECK(fwrite("new", 1, 3, f) == 3);
        CHECK(fflush(f) == 0); content("new");
        CHECK(fseek(f, 0, SEEK_SET) == 0);
        CHECK(fwrite("!", 1, 1, f) == 1);
        CHECK(fflush(f) == 0); content("new!");
        if (i >= 2) {
            CHECK(fseek(f, 0, SEEK_SET) == 0);
            CHECK(fread(bytes, 1, 4, f) == 4);
            printf("read bytes=%02x%02x%02x%02x\n", (unsigned char)bytes[0],
                   (unsigned char)bytes[1], (unsigned char)bytes[2], (unsigned char)bytes[3]);
            CHECK(!memcmp(bytes, "new!", 4));
        }
        alias = dup(fd); CHECK(alias >= 0);
        CHECK(fclose(f) == 0);
        CHECK(fcntl(fd, F_GETFL, 0) == -1 && errno == EBADF);
        if (alias >= 0) {
            CHECK(lseek(alias, 0, SEEK_SET) == 0);
            CHECK(write(alias, "?", 1) == 1); close(alias); content("new!?");
        }
    }
    seed(); fd = open("append-test", O_RDONLY); flags = fcntl(fd, F_GETFL, 0);
    errno = 0; CHECK(fdopen(fd, "a") == NULL); CHECK(errno == EINVAL || errno == EBADF);
    CHECK(fcntl(fd, F_GETFL, 0) == flags); close(fd);
    fd = open("append-test", O_WRONLY); flags = fcntl(fd, F_GETFL, 0);
    CHECK(fdopen(fd, "ab+") == NULL && errno == EINVAL);
    CHECK(fcntl(fd, F_GETFL, 0) == flags); close(fd);
    errno = 0; CHECK(fdopen(-1, "a") == NULL && errno == EBADF);
    errno = 0; CHECK(fopen("/no-such-append-directory/file", "a") == NULL && errno == ENOENT);
    f = fopen("append-test", "w"); CHECK(f != NULL);
    if (f) { CHECK(!(fcntl(fileno(f), F_GETFL, 0) & O_APPEND)); fclose(f); content(""); }
    f = fopen("append-test", "r"); CHECK(f != NULL);
    if (f) {
        fd = fileno(f);
        CHECK(freopen("/no-such-append-directory/file", "a", f) == NULL);
        CHECK(errno == ENOENT);
        CHECK(fcntl(fd, F_GETFL, 0) == -1 && errno == EBADF);
    }
    unlink("append-test");
    printf("append-stream checks=%d failures=%d\n", checks, failures);
    return failures != 0;
}
