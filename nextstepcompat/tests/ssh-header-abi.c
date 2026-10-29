/* Public signatures needed by current portable SSH. SPDX-License-Identifier: 0BSD */
#include <sys/types.h>
#include <sys/uio.h>
#include <pwd.h>
#include <grp.h>
#include <unistd.h>
#include <signal.h>

static ssize_t (*vector_write)(int, const struct iovec *, int) = writev;
static void (*signal_error(void))(int) { return SIG_ERR; }
int main(void)
{
    void (*pwent_end)(void) = endpwent;
    void (*grent_end)(void) = endgrent;
    int (*flush)(int) = fsync;
    return !vector_write || !signal_error() || !pwent_end || !grent_end || !flush;
}
