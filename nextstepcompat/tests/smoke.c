/* SPDX-License-Identifier: 0BSD */
#include <nextstepcompat.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <unistd.h>
#include <sys/stat.h>

static int checks;
#define CHECK(x) do { ++checks; if (!(x)) { \
    fprintf(stderr, "NextStepCompat failed line %d: %s\n", __LINE__, #x); return 1; \
} } while (0)

int main(int argc, char **argv)
{
    char text[128], short_buffer[4], *end, *path, *cwd;
    lldiv_t division;
    const char *directory = argc > 1 ? argv[1] : "/tmp";
    CHECK(!strcmp(NEXTSTEPCOMPAT_VERSION, "0.1.0"));
    CHECK(snprintf(text, sizeof(text), "%lld", LLONG_MIN) == 20);
    CHECK(!strcmp(text, "-9223372036854775808"));
    CHECK(snprintf(short_buffer, sizeof(short_buffer), "%s", "abcdef") == 6);
    CHECK(!strcmp(short_buffer, "abc"));
    CHECK(strtoll("-9223372036854775808!", &end, 10) == LLONG_MIN);
    CHECK(*end == '!');
    errno = 0;
    CHECK(strtoull("18446744073709551616", &end, 10) == ULLONG_MAX);
    CHECK(errno == ERANGE && *end == 0);
    CHECK(llabs(-42) == 42);
    division = lldiv(-13, 5);
    CHECK(division.quot == -2 && division.rem == -3);
    CHECK(ns33_strtod("0x1.8p+2tail", &end) == 6.0);
    CHECK(!strcmp(end, "tail"));
    CHECK(strtod("0x1.8p+2", &end) == 6.0 && *end == 0);
    CHECK(strtof("1.5", &end) == 1.5f && *end == 0);
    CHECK(strtold("1.25", &end) == 1.25L && *end == 0);
    CHECK(ns33_strcoll("a", "b") < 0);
    CHECK(strcoll("same", "same") == 0);
    CHECK(ns33_strxfrm(text, "abc", sizeof(text)) == 3 && !strcmp(text, "abc"));
    CHECK(ns33_strerror_r(EINVAL, text, sizeof(text)) == 0);
    CHECK(*text && !strcmp(text, strerror(EINVAL)));
    CHECK(ns33_strerror(-1) != 0);
    cwd = getcwd(0, 0);
    CHECK(cwd != 0);
    path = ns33_realpath(directory, 0);
    CHECK(path != 0 && path[0] == '/');
    free(path);
    path = realpath(directory, 0);
    CHECK(path != 0 && path[0] == '/');
    free(path);
    path = getcwd(0, 0);
    CHECK(path && !strcmp(path, cwd));
    free(path);
    free(cwd);
    CHECK(snprintf(text, sizeof(text), "%s/ns33-test-%ld", directory, (long)getpid()) > 0);
    CHECK(mkdir(text, 0700) == 0);
    CHECK(ns33_remove(text) == 0);
    CHECK(mkdir(text, 0700) == 0);
    CHECK(remove(text) == 0);
    printf("NextStepCompat: %d checks passed\n", checks);
    return 0;
}
