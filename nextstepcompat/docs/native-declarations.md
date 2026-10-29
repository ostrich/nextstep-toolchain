# Native declarations and stream flushing

Obsolete BSD-only prototypes conflict with POSIX wrappers or disappear when
the POSIX namespace is selected. Keep application code out of libc.h: it
reintroduces the native union-wait and readlink declarations after the modern
wrappers have already been included.

The maintained overlay now exposes account enumeration in pwd.h and grp.h,
initgroups, fsync, truncate, gethostname, killpg and crypt declarations.
SIG_ERR has the POSIX handler-pointer type, and writev accepts a const iovec
array. These declaration corrections retain the original native symbol and
ABI. They do not add a kernel interface, new runtime symbol or shared-library
slot.

The optimized four-target signature probe is tests/ssh-header-abi.c. Header
order tests and all 648 SDK checks pass against the staged bundle.

## Runtime corrections

Service-only getnameinfo queries must interpret NI flags, not the numerically
overlapping AI flags from getaddrinfo. The dedicated resolver-service probe
passes on all four NEXTSTEP targets and Intel OPENSTEP.

The native compatibility libc crashes on fflush(NULL). The wrapper uses the
original stream walker to flush output streams without closing them or
changing buffered read state. It returns the first flush error. Shared minor
10 uses a reserved export slot; existing export addresses remain unchanged.
The flush-all probe exercises dynamically allocated streams, buffered reads
and write errors on all five environments.
