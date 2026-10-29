# API coverage and implementation plan

The initial audit compares 171 C/POSIX interfaces against the default native
NEXTSTEP 3.3 library and NextStepCompat. Optimized executables were built for
Intel, NeXT 68k, SPARC and HPPA, then executed in isolated guests. Existing
compiler support and syntax-only SDK repairs remain enabled in both modes;
NextStepCompat headers and libraries are excluded from native mode.

The [procedure](../tests/coverage/README.md),
[complete availability matrix](../tests/coverage/initial-coverage.md) and
[machine-readable classifications](../tests/coverage/initial-status.json)
are maintained with the tests. Upstream inputs are pristine, MIT-licensed,
pinned libc-test files, with hashes and explicit test-harness adaptations.
This is a coverage baseline, not C or POSIX certification.
The [expanded audit](../tests/coverage/expanded-results.md) records subsequent
string/memory, stdio, environment/time and portable-API work.

## First execution batch

Ten upstream programs were attempted in both modes on all four targets.
Of 80 builds, 52 produced runnable tests. All 52 executed: 24 passed and 28
reported failures. The other 28 builds remain explicitly blocked. Each
architecture produced the same program outcomes and API availability.
Two upstream programs also fail on the Linux host, demonstrating why test
expectations need standards review rather than automatic adoption.

Selected strcspn and qsort behavior passes natively and with compatibility.
The compatibility floating-conversion and snprintf tests pass. Proven gaps
include strstr's empty-needle result and sscanf's integer-base recognition.
The mixed integer test also exposes strtol's valid base-16 prefix handling;
its invalid-base end-pointer expectation is a separate host divergence.
The ungetc program identifies fprintf's incorrect successful-write count
and a stream pushback problem following an unsuccessful scanset conversion.

Function macros are recorded separately from external symbols. For example,
fileno is exposed as a macro despite its absent external symbol. Some APIs
have symbols without public declarations. Neither case should trigger a
blind implementation of a duplicate function.

The native snprintf dependency blocks the floating-conversion program.
Missing BSD strlcpy/strlcat block the mixed string program. Missing setenv
blocks strftime. These are test dependency failures, not evidence that every
function in those programs is broken. The original assertions are preserved.

All four guests reached native shutdown states. The emulators were stopped
only afterward. Offline read-only checks passed for all seven filesystem
images. The production guest was not used or changed.

## Implementation sequence

1. Reduce the valid-input string, numeric and stdio failures to independent
   regressions. Inspect native implementation/ABI behavior before choosing
   wrappers or replacement algorithms.
2. Add a C-only string test selection, keeping BSD extensions separate.
3. Fill useful self-contained string and integer gaps. Inspect existing
   symbols and BSD equivalents first; use established implementations with
   suitable licensing where appropriate.
4. Expand filesystem/time tests, then implement wrappers only when actual
   kernel primitives support their promised semantics. Monotonic clocks,
   positional I/O and interrupt/restart behavior need specific investigation.
5. Extend the inventory to omitted math/locale facilities and header types
   and constants. Add API-family batches rather than a single giant suite.

Every implementation needs a documented contract, bounded failure behavior,
upstream or reduced regression tests, and optimized four-target execution.
Keep unsupported, partially supported, untested and broken distinct. Compiler
or application defects stay in their respective components. Existing signal,
FIFO, groups and character tests remain regression gates.

The baseline above is retained for comparison. Subsequent fixes and reviewed
execution results are recorded in
[the follow-up report](../tests/coverage/reviewed-fixes.md).

## Subsequent coverage

Threading coverage has expanded beyond the original mutex/once subset. Use
[the pthread matrix](pthread-coverage.md) and its qualification record for
current behavior and explicit limitations.

IPv4 name/service resolution, IPv4/IPv6 text conversion, BSD ASCII helpers and
explicit_bzero are implemented. IPv6 text support does not add kernel IPv6
transport. Native declarations are distinct from replacement implementations.
Positional I/O is not emulated by changing a shared descriptor offset.
See the [component overview](../README.md) and [test guide](../tests/README.md)
for the supported interfaces and separately scoped checks.

### Timestamp and math adapters

The native Intel utime NULL-buffer case faults. The namespaced replacement
supplies explicit current times; native kernel ownership restrictions still
apply, so non-owner writable-file updates are not fully POSIX-equivalent.
Explicit timestamps and owner/root current-time updates are supported.

The native Intel exponential implementation mishandles positive and negative
infinity. The namespaced double-precision exp corrects those cases and retains
the original finite-input and NaN behavior. Shared ABI minor 14 adds both
adapters without moving existing entries. The timestamp-math native regression
and C89/C++ header checks cover their public interfaces.

## Threading family

The separate [pthread API matrix](pthread-coverage.md) inventories the expanded
Cthreads/Mach implementation. Its runtime qualification and limitations are
kept separate from this C-library availability baseline.

### Binary64 math and realtime additions

NextStepCompat provides fmin, fmax, log2 and clock_gettime.
The first three use pinned musl 1.2.6 sources and namespaced public entries;
clock_gettime supplies realtime timestamps over gettimeofday. Monotonic time
remains unsupported and fails explicitly. The math header also publishes the
existing BSD acosh/asinh/atanh, hypot, cbrt, expm1/log1p and rint declarations
without changing their native implementations. stdlib.h exposes malloc_size
for callers whose native allocation layout supports it.

The focused math-clock test checks 2,390 cases, including every binary64 power
of two and generated high-precision references. Inputs are constructed from
bits so the test does not depend on native ldexp's subnormal behavior. A
separate injected-failure test checks errno propagation and output preservation.
Native qualification and its architecture-specific evidence are recorded with
the integration checkpoint; host results alone do not qualify these APIs.
