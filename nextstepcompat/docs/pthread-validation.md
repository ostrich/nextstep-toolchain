# Pthread qualification

The qualification targets optimized Linux-hosted builds against the original
NEXTSTEP 3.3 SDK: NeXT 68k, Intel, HPPA and SPARC. Intel executables also run
on OPENSTEP 4.2. All guests are disposable copies. No production desktop,
account, login configuration or system binary is changed.

## Test contents

- Native prerequisites: Cthread identity and lifecycle, per-Cproc errno,
  process-wide signal masks, actual worker/Mach identity, scheduling-policy
  queries, fixed-priority requests and queued/timed Mach IPC.
- Native spin characterization: contention in a child with a bounded alarm,
  separated from assertions about NextStepCompat's replacement.
- Retained mutex/condition tests: four workers, 8,000 protected increments,
  once publication, 400 condition handshakes and native Cthread interoperation.
- Retained TLS tests: 68 workers, 476 destructor calls, repeat/destructor limits,
  deletion/reuse/exhaustion and the unmanaged-thread boundary.
- Expanded tests: attribute validation, creation restrictions, join/detach,
  cancelled join ownership, recursive/errorcheck mutexes, deadlines and
  ownership, robust recovery/unrecoverable state and condition reacquisition,
  condition rebinding, pending/disabled cancellation, cleanup/TLS ordering,
  once rollback after cancellation and fork, 512 contended rwlock/spin updates,
  128 two-phase barrier generations, 32 cancellation/signal races, fork handler
  ordering and retained child TLS.
- Initial-thread exit: a child joins the initial thread, checks its result,
  and verifies that final process status is zero.
- Fault injection: record allocation, Mach waiter-port allocation, once
  allocation and transient-state cleanup, mutex/condition/rwlock ownership,
  barrier counts, join-claim rollback and native fork failure/error preservation.
  A separate child checks that terminated owners do not inherit stalled locks
  through recycled native handles.
  These are private static test builds; no injection hook is installed.
- C++ execution: C/native function linkage, normal RAII destruction and lexical
  cleanup. This does not establish forced C++ cancellation unwinding.
- ABI: original mutex/condition/once/attribute sizes, unchanged absolute import
  addresses on NIHS, and an unchanged older shared-library consumer.

Eight Open POSIX tests are pinned to the LTP commit recorded in
`tests/pthread-upstream/sources.json`: mutex lock/trylock, condition timed wait,
join, once, rwlock read acquisition, key associations and barrier wait. Their
source and assertions are unchanged. The build selects GNU C11 because the
historical test sources use pre-C23 empty parameter lists. A named test-only
Mach delay adapter supplies nanosleep and replaces sleep without using a
process-wide alarm. This avoids testing native sleep's threading behavior in
place of the chosen pthread assertion. It is not a production nanosleep port.

All guest processes have bounded alarms or collection deadlines. A result is
accepted only with the complete success marker, native shutdown proof,
emulator release and successful offline read-only filesystem checks. Reaching
Workspace is not a test assertion. All execution is on single-vCPU emulated
systems; physical hardware, SMP and real-time latency are not qualified.

## Native findings

| Environment | Mach timeshare query | Fixed-priority request | Native contended spin_lock |
| --- | --- | --- | --- |
| NEXTSTEP 3.3 Intel | Success | Success | Completed |
| NEXTSTEP 3.3 m68k | Success | KERN_FAILURE | Completed |
| NEXTSTEP 3.3 HPPA | Success | Success | Completed |
| NEXTSTEP 3.3 SPARC | Success | Success | Alarm-bounded hang |
| OPENSTEP 4.2 Intel | Success | Success | Completed |

SPARC libsys spin_lock's contended loop loads a byte into %o1 but tests %o0,
the nonzero lock address. Its nonblocking mutex_try_lock tests the correct
register. The native library identity and instruction addresses are recorded
in pthread-references.json. The adapter uses the nonblocking primitive in its
spin loops rather than patching the original library. Native locks inside
other libraries are not thereby repaired.

The m68k fixed-priority result demonstrates why the old kernel build options
and header constants cannot establish runtime availability on every target.
Success on the other kernels still does not prove POSIX FIFO/RR behavior,
privilege rules or priority ordering. Those policies remain explicit gaps.

## Reproduction

Use the canonical toolchain workflow in ../../docs/toolchain-workflow.md.
Build a fresh static component and shared candidate; run build-pthread-failures.py,
build-pthread-upstream.py and prepare-pthread-suite.py with their explicit
input directories. Run the resulting hashed payload on separately prepared target systems. See
[the test guide](../tests/README.md) for the entry points.
Do not select a compiler from a historical application work directory.

A complete conformance claim would additionally require all mandated libc
cancellation points, asynchronous cancellation, per-thread Unix signal state,
C++ forced unwinding, custom stack facilities and the relevant optional
scheduling/process-shared features. The API matrix identifies those gaps;
the selected upstream tests are not the full Open POSIX test suite.

## Diagnostic exclusions

SPARC qualification used deterministic instruction-counted emulation. Failed
kernel-startup runs are excluded. A deadline-helper normalization error was
corrected before qualification; invalid timespec rejection remains tested.

## Qualified result

The complete batch passes on all five environments listed above. The final
SPARC run uses deterministic icount (shift=0,sleep=off). Each run passed all
eight selected Open POSIX tests, the retained regressions, expanded tests,
allocation/fork-failure variants, unchanged older consumer and C++ fixture.
All qualified guests halted natively and passed offline filesystem checks.
The failed/paused diagnostic runs are excluded.

Shared ABI minor 20 appends 85 entries without changing any of the 204 previously
published absolute import symbols (including data/loader symbols). The public
mutex, condition, once and attribute sizes remain unchanged. Sixteen C/C++
header-order checks and all 648 SDK-header checks pass; installed header bytes
match those checked.

The normalized result record is tests/pthread-qualified-results.json. It
contains runtime/build identities and per-target log hashes without lab VM
names or host paths.
