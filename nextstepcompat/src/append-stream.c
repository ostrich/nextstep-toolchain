/* Native append streams seek once but lack O_APPEND. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>

extern FILE *native_fopen(const char *, const char *) __asm__("_fopen");
extern FILE *native_fdopen(int, const char *) __asm__("_fdopen");
extern FILE *native_freopen(const char *, const char *, FILE *) __asm__("_freopen");

static const char *native_mode(const char *mode)
{
    /* Native fdopen misparses "ab+"; binary mode has no effect on NeXT. */
    int update;
    if (mode[0] != 'r' && mode[0] != 'w' && mode[0] != 'a') return mode;
    if (strcmp(mode + 1, "b") && strcmp(mode + 1, "b+") &&
        strcmp(mode + 1, "+b")) return mode;
    update = strchr(mode, '+') != NULL;
    if (mode[0] == 'r') return update ? "r+" : "r";
    if (mode[0] == 'w') return update ? "w+" : "w";
    return update ? "a+" : "a";
}

static int enable_append(int fd)
{
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) return -1;
    if (!(flags & O_APPEND) && fcntl(fd, F_SETFL, flags | O_APPEND) < 0)
        return -1;
    return flags;
}

static FILE *finish_open(FILE *file, const char *mode)
{
    int saved;
    if (file && mode[0] == 'a' && enable_append(fileno(file)) < 0) {
        saved = errno;
        fclose(file);
        errno = saved;
        return NULL;
    }
    return file;
}

FILE *ns33_fopen(const char *path, const char *mode)
{
    return finish_open(native_fopen(path, native_mode(mode)), mode);
}

FILE *ns33_freopen(const char *path, const char *mode, FILE *file)
{
    return finish_open(native_freopen(path, native_mode(mode), file), mode);
}

FILE *ns33_fdopen(int fd, const char *mode)
{
    FILE *file;
    int flags, current, saved, access;
    mode = native_mode(mode);
    flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) return NULL;
    access = flags & O_ACCMODE;
    if ((strchr(mode, '+') && access != O_RDWR) ||
        (mode[0] == 'r' && access == O_WRONLY) ||
        ((mode[0] == 'w' || mode[0] == 'a') && access == O_RDONLY)) {
        errno = EINVAL;
        return NULL;
    }
    if (mode[0] == 'a') {
        flags = enable_append(fd);
        if (flags < 0) return NULL;
    }
    file = native_fdopen(fd, mode);
    if (!file && mode[0] == 'a' && !(flags & O_APPEND)) {
        /* A failed fdopen must leave the caller's descriptor open. */
        saved = errno;
        current = fcntl(fd, F_GETFL, 0);
        if (current >= 0) (void)fcntl(fd, F_SETFL, current & ~O_APPEND);
        errno = saved;
    }
    return file;
}
