/* Native identity, descriptor and filesystem query checks.
   SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/vfs.h>
#include <sys/stat.h>
#include <mach/mach.h>
#include <mach/host_info.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
int main(void)
{
    struct utsname name;
    kernel_version_t kernel;
    struct statfs fs;
    char hostname[256], prefix[80];
    int limit = getdtablesize();
    if (limit <= 3 || dup2(0, limit) != -1) return 1;
    if (uname(&name) || host_kernel_version(host_self(), kernel) != KERN_SUCCESS ||
        gethostname(hostname, sizeof hostname)) return 2;
    if (strlen(name.sysname) >= sizeof name.sysname ||
        strlen(name.nodename) >= sizeof name.nodename ||
        strlen(name.release) >= sizeof name.release ||
        strlen(name.version) >= sizeof name.version ||
        strlen(name.machine) >= sizeof name.machine) return 3;
    snprintf(prefix, sizeof prefix, "%s %s:", name.sysname, name.release);
    if (strncmp(kernel, prefix, strlen(prefix)) ||
        strncmp(hostname, name.nodename, sizeof name.nodename - 1)) return 4;
#if defined __i386__
    if (strcmp(name.machine, "i386")) return 7;
#elif defined __m68k__
    if (strcmp(name.machine, "m68k")) return 7;
#elif defined __hppa__
    if (strcmp(name.machine, "hppa")) return 7;
#elif defined __sparc__
    if (strcmp(name.machine, "sparc")) return 7;
#endif
    {
        const char *version = strchr(kernel, ':');
        if (!version) return 8;
        ++version;
        while (*version == ' ') ++version;
        if (strncmp(version, name.version, sizeof name.version - 1)) return 8;
    }
    errno = 0;
    if (uname(0) != -1 || errno != EFAULT) return 5;
    if (statfs(".", &fs) || fs.f_bsize <= 0) return 6;
    printf("NEXTSTEPCOMPAT system queries PASS: %s %s %s, descriptors %d\n",
           name.sysname, name.release, name.machine, limit);
    return 0;
}
