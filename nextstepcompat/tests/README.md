# NextStepCompat tests

Run these host differential checks from the component root, with output
directories outside the source tree:

```sh
python3 tests/path-host.py --output /path/to/checks/paths
python3 tests/parse-host.py --sanitize --output /path/to/checks/parsing
python3 tests/integer-host.py --output /path/to/checks/integers
python3 tests/singlebyte-host.py --output /path/to/checks/singlebyte
```

They use the host C compiler and libc as references. The parsing test uses
AddressSanitizer and UndefinedBehaviorSanitizer when `--sanitize` is given.
These checks do not establish target ABI or guest execution correctness.

With an integrated cross-toolchain, build the target API smoke test:

```sh
nextstep-gcc --sdk /path/to/sdk33 -arch i386 -O2 tests/smoke.c -o compat-test
```

Repeat for the other targets, or repeat `-arch` to make a fat executable.
Run the result in a disposable target environment, optionally supplying an
existing writable test directory as its first argument. The default is
`/tmp`. The test exercises both standard spellings and explicit `ns33_`
adapters and reports its own assertion count. It creates and removes only
its uniquely named test directory.

Build `tests/singlebyte.c` the same way for the exhaustive character contract
test. It checks the 16-bit wide ABI, native header mappings, conversion bounds,
classification and string/memory operations. The host single-byte runner uses
a private symbol namespace and 16-bit wchar_t; it does not interpose these
functions into the host C library.

The compiler repository additionally checks fat linking, extracted slices,
header independence, original SDK layouts and C/C++ runtime integration.

The signals.c and fifo.c target tests exercise native signal and FIFO behavior.
Build with the same driver command above, replacing smoke.c with the test
filename. Run each as root only in a disposable guest: they drop to uid/gid 1
and have bounded alarm timeouts. FIFO creates and removes its own temporary
directory; signals uses child processes and temporary signal dispositions.
The original parent shell's credentials and signal state are unaffected.

Build regex.c with the same integrated driver command for POSIX matching,
leftmost/longest selection, captures, execution/compilation flags, single-byte
high-bit input, invalid patterns, bounded error descriptions and allocation/
free repetition. The case expectations also run against the host libc as a
reference with a plain cc -O2 build. Its summary counts checks, including
repeated lifecycle checks, rather than distinct expression patterns.

Run groups.c as root only in a disposable guest. Its child installs a known
supplementary group set, drops to uid/gid 1 and checks POSIX group values,
count queries, bounds canaries and invalid arguments against native BSD
results. Only the child changes credentials; the parent identity is preserved.

The systematic [C library/POSIX coverage audit](coverage/README.md) compares
native and compatibility declarations, link availability and selected pinned
upstream behavior tests across all four NEXTSTEP 3.3 targets.

The focused libc-regressions.c test reduces the coverage failures and checks
numeric boundaries, scansets, stream counts, pushback/EOF and error states.
Build it without NS33_EXTENDED for a native-only negative control, and with
-DNS33_EXTENDED for the compatibility run, including length modifiers, wide
characters, positional arguments and caller-owned buffer boundaries.

Run algorithm checks on the host with:

```sh
python3 tests/libc-host.py --sanitize --output /path/to/checks/libc
```

This replays the pinned formatting/scanning adaptations in a private namespace
and tests them with host sanitizers. Host FILE has a different layout; the
NeXT pushback and error-state bridges require the actual guest regressions.

Use integer-host.py --check-ilp32 when the host has multilib C support to
compare 32-bit long conversions as well as host-width and long-long results.

The `make-headers.c` regression checks the header gaps found by pristine
GNU Make: numeric feature macros, builtin alloca, a stable `struct dirent`
tag across forward declarations, native directory offsets, wait3 status
words, vfork, temporary files and truncation. It also checks putenv's
caller-owned buffer, replacement by setenv, removal and invalid names.
Build and run it with the same optimized driver invocation above on each
architecture. Its temporary file is removed before child-process checks.
The environment ownership tests also run under the host sanitizers through
`portable-host.py`.

Threading and byte-order adapters
--------------------------------

`threads.c` checks four native workers, contended mutex increments, once
publication, main/worker identities, busy/invalid controls, quiescent fork
behavior, 400 condition-variable handshakes and byte-order conversions.
Condition tests cover dynamic/static initialization, four broadcast waiters,
signal-based progress, mutex reacquisition and busy/invalid controls. A
45-second alarm bounds a deadlock.
It uses native cthreads for creation/join; those pthread entry points are not
part of the current subset. It does not test recovery from a multithreaded
fork with a mutex or initializer held by a vanished thread.

Build with `build-threads.py --toolchain <bundle> --sdk <sdk33> --compat
<component-build> --output <fresh-tests>`. For a shared NextStepCompat SDK,
add `--shared`. The recipe records source, import-library and toolchain
identities and emits a NIHS `threads` executable. Use
`test-openstep-threads.py --build <tests> --agent-client <client.py> --socket
<isolated-guest.sock>` for Intel OPENSTEP, adding `--runtime <runtime.shlib>`
for the shared test. It refuses existing guest paths and removes only the
files it uploaded. The same executable must also be exercised on the four
NEXTSTEP target guests before claiming NIHS runtime validation.

Network and BSD header regressions
---------------------------------

`build-network.py` has the same toolchain/SDK/component/output options as the
threading builder. It builds a real-database probe and, for static components,
a separate probe with controlled native database/interface fixtures. The
fixtures exercise temporary lookup failures, multiple addresses and transports,
copying of reused native storage, concurrent lookups and AI_ADDRCONFIG failure
paths. They do not replace the production adapter code.

`test-openstep-network.py` runs the probes in an isolated configured guest and
cleans up its uploaded files. The real-database test expects localhost and the
domain service to resolve and a non-loopback IPv4 interface to be configured.
The default probe, without --native-databases, avoids these environmental
requirements for installation-root tests. IPv6 text parsing is tested separately
from the native kernel's rejection of IPv6 sockets.

The printed check total also includes exhaustive ASCII macro/function cases,
bounded explicit_bzero checks and header/native-call regressions. It should not
be described as thousands of independent DNS or protocol tests. Intel static/shared checks exercise these separately from real-database
lookups; environment-dependent DNS checks require their stated prerequisites.

`termios.c` opens a free BSD pty pair, changes and restores ECHO with each
tcsetattr action, checks TCSASOFT does not modify caller data, and checks invalid
action/descriptor errors. Build optimized NIHS copies against both static and
shared NextStepCompat. The extended native-PTY regression also covers all four NEXTSTEP targets;
physical serial break timing remains untested.

math-constants.c checks C99 floating constant types in C and C++, then reads
volatile NaN/infinity values and verifies their native IEEE representation.
Compile through nextstep-gcc -std=gnu11 or nextstep-g++ -x c++ -std=gnu++17
for each target. It does not require new runtime symbols or change shared ABI.

Allocation guards
-----------------

Run allocator-guards.c with the host compiler and address/undefined sanitizers.
It substitutes controlled native operations; large boundary checks do not
allocate gigabytes. For target builds, use build-allocation.py --toolchain
<fresh-stage> --sdk <sdk33> --output <fresh-tests>, optionally adding --shared
<canonical-shared-build>. The three optimized NIHS probes cover native pointer
interoperability, large/overflow rejection, zero sizes, realloc preservation,
and imported formatting/string allocation errors. Record guest execution
separately from compilation. See ../docs/native-allocator-limits.md for the
bound derivation and remaining native allocator limitations.

file-types.c checks the missing modern POSIX symbolic-link and socket
predicates against the native SDK file-mode bits. Constant assertions compile
in C and C++ for NIHS; the Intel OPENSTEP run additionally checks that each
macro evaluates its argument once. The associated header-only change leaves all four static runtime
archives unchanged.

filesystem-declarations.c checks fchmod/fchown/symlink/mknod in their modern
headers using the native libc.h argument types, and performs private temporary
file/FIFO/link operations. The C-only coexistence check isolates the native
header's unrelated legacy wait3/readlink declarations. The unchanged C and C++
16-check versions pass on NIHS and OPENSTEP in native execution. The added chroot declaration has a separate safe
negative check against a regular file, which cannot change the process root.


`thread-keys.c` checks managed POSIX thread creation/exit, thread-specific values,
key deletion/reuse/exhaustion, destructor repetition and the four-iteration
limit. Build it with `build-threads.py --source thread-keys`; the output still
uses the `threads` executable name. Run it through a hashed generic suite or
an isolated NIHS guest. The older test-openstep-threads.py helper expects the
mutex/condition fixture's marker and is not the runner for this fixture.
See [thread lifecycle](../docs/thread-lifecycle.md) for the native-thread
ownership boundary and recorded evidence.

The extended `termios.c` regression checks encoded speeds, invalid arguments,
flow stop/start, transmitted control characters, disabled control characters,
flushing, draining and break errors on a native PTY. It has a 15-second alarm.
`sprintf.c` checks significant-digit rounding, long output, return counts,
%n, positional arguments and direct va_list formatting. Physical serial break timing remains untested.

`rewinddir.c` checks repeated rewinds after EOF across multiple native directory
buffers, preserves entry order, and removes its private fixture directory.
The native prototype's missing implementation is supplied in shared minor 13.

## Expanded pthread qualification

The [API matrix](../docs/pthread-coverage.md),
[implementation contracts](../docs/pthreads.md) and
[qualification record](../docs/pthread-validation.md) distinguish supported
semantics from native limitations. Record the qualified bundle used for a build.
Use fresh output directories and disposable test guests.

Build the static component with ../build.py and the shared candidate with
../build-shared.py. Then use:

- build-pthread-failures.py with the static component to build private
  allocation-fault variants. Its injected entry points are never installed.
- build-pthread-upstream.py with the shared candidate to build eight pinned
  Open POSIX tests. Original files and assertions remain unchanged. The
  explicitly named test timing helpers are not system nanosleep replacements.
- prepare-pthread-suite.py with --shared, --failures, --upstream and an
  optional --old-consumer to assemble one hashed payload. Execute that payload on separately prepared target systems.
- build-threads.py --source pthread-cxx to check C++/native linkage, ordinary
  RAII and lexical cleanup. Forced C++ cancellation unwinding is not claimed.
- check-pthread-abi.py to compare old/new shared import addresses on NIHS.

pthread-native.c records real Mach scheduling policy, process-wide signal
masks, per-Cproc errno and IPC behavior. pthread-native-spin.c characterizes
native spin_lock in an alarm-bounded child. An observed native hang is a
platform finding, not success for the compatibility implementation; the
expanded stress fixture separately tests our replacement path.

pthread-expanded.c covers attributes, detach and join ownership, timed locks,
robust owner death and recovery, condition rebinding, cancellation state and
cleanup ordering, once rollback across cancellation/fork, rwlocks, barriers,
spinlocks, and native fork integration. Older threads.c and thread-keys.c
remain regression gates. pthread-exit.c separately checks initial-thread exit.

`build-math-clock.py` builds a fat regression binary for the binary64 fmin,
fmax and log2 APIs and realtime clock_gettime. Its reference-table generator
uses a fixed random seed and 160-digit Decimal logarithms, then checks the
committed table before compiling. Supply --toolchain, --sdk, --compat and
--output; --shared selects a shared-library build directory. Run math-clock
on each target. It includes all binary64 powers of two, numerical vectors
with a one-ULP bound, special values, errno, realtime representation and
explicit failure for unsupported clocks. Clock bracketing assumes the system
wall clock is not administratively changed during the test.

Run math-clock-host.py --output /path/to/checks/math-clock --sanitize to replay
the pinned source adapters and execute the numerical/realtime checks under
ASan/UBSan. It also runs clock-failures.c with an injected gettimeofday failure.
This checks propagation of the native error and preservation of the caller's
output. It does not emulate a target ABI or replace native execution.
