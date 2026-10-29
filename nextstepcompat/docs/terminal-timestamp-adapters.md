# Terminal, directory and timestamp adapters

Several terminal functions declared in the NEXTSTEP SDK have no libsys
implementation. Shared minor 11 adds cfgetispeed, cfgetospeed, cfsetispeed,
cfsetospeed, ctermid, tcdrain, tcflow, tcflush and tcsendbreak using the
native termios structure and BSD ioctls.

The SDK's speed values are encoded constants, not numeric baud rates. The
adapter regression uses native PTYs. Serial break timing still requires
physical hardware validation. Nonzero break durations select a quarter second.

The native sprintf has a precision bug: %.15g formats 123.456 as
123.456000000000003. Shared minor 12 binds sprintf and vsprintf to the
existing maintained formatter using ns33_ entry points. The regression covers
precision, long output, return counts, positional arguments and the va_list
entry.

Both optimized regressions pass on NEXTSTEP 3.3 NIHS. Each guest halts
natively and its stopped filesystem checks pass. All previously occupied
function slots remain at their original addresses.

wait4 is a native libsys declaration, not a new compatibility implementation.
The [wait investigation](waitpid-investigation.md) documents why it cannot be
forwarded as a general POSIX waitpid. No generic waitpid implementation has
been promoted.

Shared minor 13 adds ns33_rewinddir. The original SDK's POSIX profile declares
rewinddir but libsys has no corresponding entry; its BSD profile used
seekdir(directory, 0) as a macro. The maintained function uses that native
implementation and a namespaced public binding. Its regression creates a
directory spanning multiple buffers, reads to EOF, rewinds twice and checks
entry order and cleanup. It passes on NIHS, with native halt and clean
filesystem checks. Existing occupied export slots are unchanged; further
unused slots have been reserved.

## Timestamp and exponential adapters

The Intel native probe confirms that utime(path, NULL) dereferences its time
buffer and raises SIGBUS. utimes(path, NULL) returns an error. ns33_utime
supplies explicit current timestamps obtained with gettimeofday, while passing
explicit caller timestamps to the native implementation unchanged. Empty paths
are rejected. The original kernel ownership checks remain: current-time
updates to a non-owner writable file can still return EPERM. This is a kernel
restriction, not full emulation of modern timestamp permissions.

Native Intel exp(+Inf) and exp(-Inf) return NaN. ns33_exp handles those two
inputs directly and delegates finite values and NaNs to the original function.
Its public header preserves the SDK's function type, including the historical
qualified return type in C89 and C++ modes.

Both functions occupy previously reserved entries in shared ABI minor 14.
Existing entries retain their positions. tests/timestamp-math.c checks
explicit and current timestamps, errors, native non-owner permissions, finite
results, NaNs, infinities, positive zero and errno preservation.
Qualification: the shared minor-14 runtime passes 27 native timestamp/math
checks on each of Intel, NeXT 68k, HPPA and SPARC, with native halts and clean
stopped filesystem checks. All four report EPERM for the non-owner writable
file case. SDK checks pass 648/648 and the public C/C++ header-order checks
pass.
