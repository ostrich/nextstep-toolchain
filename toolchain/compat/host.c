#define _GNU_SOURCE 1
#include "host.h"
#include <errno.h>
#include <sys/mman.h>
#include <mach/mach.h>
#include <mach/mach_error.h>
#include <mach-o/dyld.h>
size_t strlcpy(char *dst, const char *src, size_t size)
{
    size_t n = strlen(src);
    if (size) { size_t copy = n < size - 1 ? n : size - 1; memcpy(dst, src, copy); dst[copy] = 0; }
    return n;
}
size_t strlcat(char *dst, const char *src, size_t size)
{
    size_t d = strnlen(dst, size), s = strlen(src);
    if (d < size) strlcpy(dst + d, src, size - d);
    return d + s;
}
void *reallocf(void *p, size_t n) { void *q = realloc(p, n); if (!q && n) free(p); return q; }
char *mach_error_string(mach_error_t e) { return strerror(e); }
mach_port_t mach_task_self_;
mach_port_t mach_host_self(void) { return 0; }
kern_return_t mach_port_deallocate(ipc_space_t t, mach_port_name_t n) { return KERN_SUCCESS; }
kern_return_t host_info(host_t h, host_flavor_t f, host_info_t out, mach_msg_type_number_t *n)
{
    if (f != HOST_BASIC_INFO || *n < HOST_BASIC_INFO_COUNT) return KERN_INVALID_ARGUMENT;
    memset(out, 0, sizeof(struct host_basic_info));
    ((host_basic_info_t)out)->cpu_type = CPU_TYPE_I386;
    ((host_basic_info_t)out)->cpu_subtype = CPU_SUBTYPE_I386_ALL;
    *n = HOST_BASIC_INFO_COUNT;
    return KERN_SUCCESS;
}
kern_return_t vm_allocate(vm_map_t t, vm_address_t *a, vm_size_t n, int flags)
{
    void *p;
    if (!n) { *a = 0; return KERN_SUCCESS; }
    if (!flags) return KERN_NOT_SUPPORTED;
    p = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return KERN_NO_SPACE;
    *a = (vm_address_t)p; return KERN_SUCCESS;
}
kern_return_t vm_deallocate(vm_map_t t, vm_address_t a, vm_size_t n)
{
    return !n || munmap((void *)a, n) == 0 ? KERN_SUCCESS : KERN_INVALID_ADDRESS;
}
kern_return_t map_fd(int fd, vm_offset_t offset, vm_offset_t *a, boolean_t anywhere, vm_size_t n)
{
    void *p;
    if (!anywhere) return KERN_NOT_SUPPORTED;
    p = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, offset);
    if (p == MAP_FAILED) return KERN_FAILURE;
    *a = (vm_offset_t)p; return KERN_SUCCESS;
}
int _NSGetExecutablePath(char *buf, uint32_t *size)
{
    /* Direct invocation of a private ELF loader makes /proc/self/exe name
     * that loader. Our launcher supplies the actual image for sibling tools. */
    const char *image = getenv("NEXTSTEP_HOST_EXECUTABLE");
    if (image && image[0] == '/') {
        size_t length = strlen(image);
        if (length >= UINT32_MAX) return -1;
        if (*size <= length) { *size = (uint32_t)length + 1; return -1; }
        memcpy(buf, image, length + 1);
        return 0;
    }
    size_t capacity = 256;
    char *temporary = NULL;
    ssize_t n;
    for (;;) {
        char *grown = realloc(temporary, capacity);
        if (!grown) { free(temporary); return -1; }
        temporary = grown;
        n = readlink("/proc/self/exe", temporary, capacity);
        if (n < 0) { free(temporary); return -1; }
        if ((size_t)n < capacity) break;
        if (capacity > UINT32_MAX / 2) { free(temporary); return -1; }
        capacity *= 2;
    }
    if (*size <= (uint32_t)n) {
        *size = (uint32_t)n + 1;
        free(temporary);
        return -1;
    }
    memcpy(buf, temporary, n);
    buf[n] = 0;
    free(temporary);
    return 0;
}

/* RFC 4122 version 4 UUIDs for the optional Mach-O UUID command. */
#include <sys/random.h>
void uuid_generate_random(unsigned char *p)
{
    size_t done = 0;
    while (done < 16) {
        ssize_t n = getrandom(p + done, 16 - done, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { perror("getrandom"); exit(1); }
        done += n;
    }
    p[6] = (p[6] & 15) | 64;
    p[8] = (p[8] & 63) | 128;
}

/* BSD archive verbose-listing permissions. */
#include <sys/stat.h>
void strmode(mode_t mode, char *text)
{
    static const mode_t bits[] = {S_IRUSR, S_IWUSR, S_IXUSR, S_IRGRP,
        S_IWGRP, S_IXGRP, S_IROTH, S_IWOTH, S_IXOTH};
    static const char letters[] = "rwxrwxrwx";
    text[0] = S_ISDIR(mode) ? 'd' : S_ISLNK(mode) ? 'l' :
        S_ISCHR(mode) ? 'c' : S_ISBLK(mode) ? 'b' :
        S_ISFIFO(mode) ? 'p' : S_ISSOCK(mode) ? 's' : '-';
    for (unsigned i = 0; i < 9; ++i)
        text[i + 1] = mode & bits[i] ? letters[i] : '-';
    if (mode & S_ISUID) text[3] = mode & S_IXUSR ? 's' : 'S';
    if (mode & S_ISGID) text[6] = mode & S_IXGRP ? 's' : 'S';
    if (mode & S_ISVTX) text[9] = mode & S_IXOTH ? 't' : 'T';
    text[10] = ' ';
    text[11] = 0;
}
