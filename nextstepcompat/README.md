# NextStepCompat

NextStepCompat supplies reusable C library compatibility functions for
NEXTSTEP 3.3 applications, also intended to run on OPENSTEP 4.2. It is built
with the modern NeXT cross compiler for Intel, NeXT 68k, SPARC and HPPA.
The compiler's default links it statically without a separate guest
installation. Ports with shared dependency packages can instead use the
fixed-VM shared runtime.

The component owns its sources, public headers, pinned upstream inputs,
licenses and build script. It can be copied out of the compiler repository
and built independently. Original SDK headers and libraries remain external.

The stdio overlay supplies append-mode fopen, fdopen and freopen wrappers.
They enable the native descriptor's O_APPEND flag so writes continue to
append after seeks or truncation. The wrappers also normalize standard
binary mode spellings for native fdopen and validate descriptor access
without taking ownership when fdopen fails. Stream buffering and allocation
remain owned by native libc. Shared clients using these wrappers require
runtime minor version 22 or later; existing export slots are preserved.

## Build

Using a compiler bundle with NextStepCompat support:

```sh
python3 build.py --toolchain /path/to/toolchain --sdk /path/to/sdk33 \
  --output /path/to/build/nextstepcompat
```

The default builds all four targets and a fat `libnextstepcompat.a`.
Repeat `--arch` to select particular targets. Each target's archive and
objects are under its architecture directory. `build-record.json` records
input hashes, commands and output hashes. Builds use `-O2`; the original
third-party sources stay unchanged and their adaptation patches are applied
to private build copies without fuzz.

To construct the shared runtime and its import archive from a verified
compiler installation:

```sh
python3 build-shared.py --toolchain /path/to/toolchain --sdk /path/to/sdk33 \
  --output /path/to/build/nextstepcompat-shared
```

This recompiles shared-runtime intermediates with canonical function entries
and produces libnextstepcompat.1.shlib and a link-time libnextstepcompat.a.
Install the runtime with mode 0755. Function slots and reserved address ranges
are maintained in shared.json; do not reorder occupied slots. Shared builds
use the native system runtime's environment bridge so native getenv and
shared environment updates observe the same process environment. Compiler
helpers remain private. See the toolchain shared-library documentation for
dependency construction and runtime regression checks.

The intermediate component's function definitions are isolated for construction;
it is not a replacement static library. install.py rejects those intermediates.
The ordinary build.py default continues to produce the static compiler component.

To update only this component in an existing compiler installation:

```sh
python3 install.py --toolchain /path/to/toolchain \
  --build /path/to/build/nextstepcompat --backup /path/to/new-backup
```

This replaces the component's headers and four libraries and updates the
bundle's integrity manifest. GCC and other runtime binaries are retained.
Applications need rebuilding to incorporate static-library changes.

For compiler bootstrapping, `--cc` accepts a shell-quoted compiler-driver
command and `--tools` selects the matching classic Mach-O tools. The command
is parsed into arguments and executed directly, without a shell. The build
script still supplies the SDK, architecture and compatibility-header options.

## Use

The integrated compiler selects these headers and libraries automatically:

```sh
nextstep-gcc --sdk /path/to/sdk33 -arch i386 -O2 program.c -o program
nextstep-gcc --sdk /path/to/sdk33 -arch i386 -arch m68k -arch sparc \
  -arch hppa -O2 program.c -o program-fat
```

Normal C interfaces retain their standard spellings. Where a correction must
coexist with a native symbol, the headers map it to an `ns33_` adapter.
`nextstepcompat.h` also declares those adapters explicitly. Neither public
adapters nor new private mappings use the older `os42_` prefix.

Maintainers can use `--compat-headers DIR` to replace the compiler's installed
compatibility-header directory when rebuilding this component. It does not
replace the linked library, so it should normally be used for object builds.
Avoid adding a second copy of the compatibility wrappers with `-I`.

## Scope

Current implementations provide bounded and stream integer/floating formatting,
full-width integer conversions, floating-point parsing, reentrant path
resolution, directory access and selected C-locale/error adapters. The
headers also bridge the original SDK's declarations and native directory ABI.
Formatting and parsing adaptations retain their pinned musl baselines and
license notices. See `format/README.md`, `parse/README.md` and `scan/README.md`
for details. `string/README.md` covers string search, unsigned byte comparisons
and portable string additions. `time/README.md` describes C-locale calendar
formatting and the native-locale fallback.

Additional portable interfaces include strdup, strndup, strnlen, strtok_r,
getline/getdelim and the narrow-string intmax conversion/arithmetic family.
Line input preserves embedded NULs, grows caller-owned buffers and checks the
native ssize_t limit. It retains the original FILE buffering and locking
limitations. Wide-string intmax conversions remain unavailable.

setenv, unsetenv and putenv share native environ/getenv. setenv copies values;
putenv retains the caller's buffer, so later edits remain visible. They reclaim
their own replaced strings without freeing inherited or caller-owned strings.
Environment mutation is process-global and is not thread-safe or async-signal-
safe. If an application replaces environ itself, a previously exported pointer
table is retained because the caller may still reference it.

This is not a replacement libc or a Unicode implementation. It does not
implement every function declared in the SDK. Compiler arithmetic helpers,
exceptions, compiler TLS, atomics and floating-point startup belong to the
compiler runtime, not this component. POSIX API adapters over native Cthreads
are maintained here. Extended floating precision still
requires the compiler's startup support on applicable targets.

The single-byte character layer provides restartable conversion, wide string
operations, native character classification and display widths. It preserves
the 16-bit wide-character ABI and reserves conversion state for later
encodings. See [single-byte behavior](docs/singlebyte.md) for the exact contract
and [tests](tests/README.md) for reproducible checks. No UTF-8 locale or wide
stream I/O is added.

The POSIX signal layer provides signal-set operations, sigprocmask, sigpending,
sigsuspend and sigaction using the native process-wide signal model. Handler
installation preserves libc's trampoline and maps restart behavior explicitly.
SA_RESTART and SA_ONSTACK are supported; SA_NOCLDSTOP and unknown flags are
rejected with EINVAL. This is not pthread signal support or full modern POSIX
signal conformance. See [signal and FIFO behavior](docs/signals-fifo.md).

The standard mkfifo interface creates native filesystem FIFOs through mknod.
No driver, daemon or separate guest package is needed.

The POSIX regex layer provides regcomp, regexec, regfree and regerror using
pinned musl 1.2.6/TRE sources. It uses the single-byte character layer and
standard POSIX symbols, distinct from the SDK's unrelated legacy regex API. See
[regex implementation](regex/README.md) for the ABI, locale and license scope.

The getgroups adapter converts the native BSD int array into the SDK's
smaller POSIX gid_t elements and supports count-only queries. It validates
array size before copying and binds standard calls to ns33_getgroups while
leaving the native BSD symbol available. This avoids both incorrect group
values and writes beyond caller arrays compiled against the POSIX header.

The [API coverage audit](tests/coverage/README.md) records the standards scope,
native/compatibility comparison procedure and upstream test provenance.
The [first results and implementation sequence](docs/api-coverage.md) identify
verified gaps separately from blocked tests and untested interfaces.

The coverage-driven adapters correct strstr's empty-needle result and the
native strtol/strtoul prefix, sign, overflow and end-pointer behavior. The
latter reuse the existing checked full-width integer conversion routine.
Formatted input uses the pinned musl scanner for sscanf/fscanf/scanf and their
va_list variants. Stream output uses the existing musl formatter through a
native buffering bridge. Header aliases leave original system symbols intact.

### POSIX threading compatibility

`pthread.h` provides managed thread creation, join/detach and exit, validated
attributes, TLS with destructors, cleanup handlers and deferred cancellation.
Synchronization includes normal, recursive, error-checking and managed robust
mutexes, timed conditions and locks, rwlocks, reusable barriers, spinlocks and
once initialization. Scheduling supports SCHED_OTHER/priority zero. The fork
overlay runs registered handlers and repairs the adapter's child-side state.
Public entries are namespaced ns33_ functions; native libsys is not replaced.

This is not a complete POSIX threads implementation. Custom stacks, realtime
scheduling, priority inheritance/protection, process-shared synchronization,
asynchronous cancellation and per-thread Unix signal delivery/masking remain
unsupported. Native libc blocking calls are not cancellation points. Foreign
Cthreads can use ordinary synchronization, but TLS, robust ownership and exit
cleanup require the managed lifecycle. Read the [API matrix](docs/pthread-coverage.md),
[contracts and native research](docs/pthreads.md), and
[test scope](docs/pthread-validation.md) before relying on these distinctions.

`termios.h` supplies `tcgetattr` and `tcsetattr` through the native terminal
ioctls. Immediate, drain and flush actions are supported, along with the native
TCSASOFT flag. Invalid actions return EINVAL. This does not emulate a terminal
driver or add missing kernel behavior.

`endian.h` supplies single-evaluation BSD host/big/little-endian conversions
at 16, 32 and 64 bits using the target compiler's byte-order definitions.

### Network and related BSD interfaces

The IPv4 resolver adapters provide getaddrinfo, freeaddrinfo, getnameinfo and
gai_strerror using the original host/service databases. They support TCP and
UDP, numeric addresses and services, canonical names, passive addresses and
AI_ADDRCONFIG. Raw-socket resolution and the NI_NOFQDN extension are not
implemented. Calls through these adapters serialize native database access and
copy results before releasing the lock. Direct calls to the old non-reentrant
resolver functions still require caller synchronization.

inet_pton and inet_ntop use pinned musl code for IPv4 and IPv6 text conversion.
IPv6 structures are available for certificate/address data. The data-only
AF_INET6 value lies outside the native kernel domain table; it does not enable
IPv6 sockets or resolution. NS33_IPV6_DATA_ONLY identifies this distinction.
socklen_t is an int to match the original socket calls and their result-length
pointers. The wrappers also publish the existing select, shutdown, getpagesize
and vsyslog declarations. FD_ZERO uses builtin memset, avoiding the SDK's
undeclared bzero call in POSIX mode.

The BSD isascii/toascii extensions have single-evaluation macros and addressable
function forms. explicit_bzero uses musl's memory-barrier implementation and is
built with optimization, rather than relying on an unoptimized clearing routine.
These additions use reserved shared-library slots and require minor version 3.

Focused network, resolver, ASCII, zeroing and socket tests build on NIHS and
pass with both static and shared NextStepCompat on Intel OPENSTEP. See the component test guide for the separately scoped native resolver checks.
These are scoped compatibility results, not a complete POSIX conformance claim.

## Native system limit queries

sysconf supplies the ten selectors declared by the NEXTSTEP SDK. It uses
getdtablesize for the process descriptor limit and the SDK's published values
for the remaining selectors. Unknown selectors fail with EINVAL. This does
not add newer POSIX feature claims or selectors absent from that SDK.

tests/build-sysconf.py builds an optimized NIHS probe covering the selectors,
invalid values, errno preservation and forked descriptor cleanup. Static
execution passed on all four NEXTSTEP targets and Intel OPENSTEP; shared
execution was checked on Intel OPENSTEP. These are scoped API checks.

The terminal adapters also provide native speed accessors, output draining,
queue flushing, flow control and timed breaks, plus ctermid. They use the
original BSD terminal ioctls and encoded NeXT baud constants. A nonzero break
duration selects the same quarter-second interval as zero. Physical serial
line timing needs hardware validation; the regression uses native PTYs.

Unbounded sprintf and vsprintf use the same maintained formatter as snprintf.
This corrects the native formatter exceeding its requested significant-digit
precision for values such as 123.456, while retaining the standard caller-owned
buffer contract. Public calls bind to ns33_ symbols and do not replace libsys.

The wait header exposes libsys's native wait4 entry. Its selector and signal
semantics differ from POSIX waitpid; no waitpid implementation is exported.
See [the native wait investigation](docs/waitpid-investigation.md) before using
it to adapt application-specific child handling.

rewinddir uses the native BSD seekdir(directory, 0) operation. The POSIX SDK
prototype alone cannot link on NEXTSTEP, so calls bind to ns33_rewinddir in
shared minor 13. Native NIHS directory-buffer and rewind regressions pass;
see [terminal and timestamp adapters](docs/terminal-timestamp-adapters.md).

The utime adapter supplies current timestamps without passing a NULL buffer to
the original implementation. Native ownership restrictions remain, including
EPERM for current-time updates to non-owner writable files. The exp adapter
corrects the native positive/negative-infinity cases while retaining finite
and NaN behavior. Both use reserved entries in shared minor 14. The native
27-check timestamp/math regression passes on NIHS, as do all 648 SDK header
checks and C/C++ header-order checks; see the terminal and timestamp adapter notes.

Shared minor 15 adds namespaced getopt/getopt_long state, result-buffer time
conversions, strsignal, stpcpy, strcasestr and C99 rounding helpers. The option
parser and float algorithms use pinned musl release sources. Function entries
remain stable; option globals occupy explicit data slots. See
[terminal-port integration](docs/options-time-math.md) for contracts and regression
scope. These additions do not emulate missing kernel scheduling or wait flags.

System identity uses ns33_uname over native Mach and BSD queries, preserving
NEXTSTEP's original five-field utsname layout and its 32-byte field limits.
It reports the actual kernel identity, host name and supported machine family,
rather than guessing a userland OS version. The system-query regression passes
on NEXTSTEP 3.3 NIHS and Intel OPENSTEP 4.2. Shared ABI minor 19 adds the entry
without moving existing public function addresses.

### Binary64 math and realtime timestamps

The compatibility math header exposes native BSD functions that the SDK hides
in POSIX mode. Missing fmin, fmax and log2 use pinned musl implementations,
with private names and unchanged log2 polynomial coefficients. They handle
signed zero, infinities and NaNs; log2 also reports domain and pole errors.
See [math sources and adaptations](math/README.md).

clock_gettime supports CLOCK_REALTIME through native gettimeofday with
microsecond resolution expressed as nanoseconds. It is a wall clock and may
jump when system time changes. CLOCK_MONOTONIC returns ENOTSUP; other unknown
clock IDs return EINVAL. Failure leaves the output structure unchanged. This
adapter does not provide a monotonic execution-deadline clock.
