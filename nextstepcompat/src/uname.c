/* Mach kernel identity using the original NEXTSTEP utsname layout.
   SPDX-License-Identifier: 0BSD */
#include <sys/utsname.h>
#include <mach/mach.h>
#include <mach/host_info.h>
#include <mach/machine.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

static void field(char *destination, size_t capacity, const char *source, size_t length)
{
    if (length >= capacity) length = capacity - 1;
    memcpy(destination, source, length);
    destination[length] = 0;
}

int uname(struct utsname *result)
{
    struct utsname value;
    struct host_basic_info info;
    unsigned int count = HOST_BASIC_INFO_COUNT;
    kernel_version_t kernel;
    char hostname[256];
    const char *machine, *colon, *release, *version;
    size_t prefix;
    if (!result) { errno = EFAULT; return -1; }
    if (host_kernel_version(host_self(), kernel) != KERN_SUCCESS ||
        host_info(host_self(), HOST_BASIC_INFO, (host_info_t)&info, &count) != KERN_SUCCESS) {
        errno = EIO; return -1;
    }
    if (gethostname(hostname, sizeof hostname)) return -1;
    hostname[sizeof hostname - 1] = 0;
    switch (info.cpu_type) {
    case CPU_TYPE_I386: machine = "i386"; break;
    case CPU_TYPE_MC680x0: machine = "m68k"; break;
    case CPU_TYPE_HPPA: machine = "hppa"; break;
    case CPU_TYPE_SPARC: machine = "sparc"; break;
    default: errno = ENOTSUP; return -1;
    }
    /* Kernels identify themselves as "NeXT Mach <release>: <build>".
       Report those queried fields, rather than claiming a userland OS version. */
    colon = strchr(kernel, ':');
    prefix = colon ? (size_t)(colon - kernel) : strlen(kernel);
    release = kernel + prefix;
    while (release > kernel && release[-1] != ' ') --release;
    if (release == kernel || release == kernel + prefix) { errno = EIO; return -1; }
    version = colon ? colon + 1 : kernel;
    while (*version == ' ') ++version;
    memset(&value, 0, sizeof value);
    field(value.sysname, sizeof value.sysname, kernel, (size_t)(release - kernel - 1));
    field(value.release, sizeof value.release, release, (size_t)(kernel + prefix - release));
    field(value.version, sizeof value.version, version, strlen(version));
    field(value.nodename, sizeof value.nodename, hostname, strlen(hostname));
    field(value.machine, sizeof value.machine, machine, strlen(machine));
    *result = value;
    return 0;
}
