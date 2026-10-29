# Native atomic operations

The development runtime builds the original GCC libatomic algorithms with
tools/build-libatomic.py. The GCC patch adds NEXTSTEP configuration and a
small lock adapter. Original release sources and the ordered patches remain
separate. SDK files are private.

The fallback uses one native cthreads spin lock for both sized and generic
operations. It requires no thread initialization, allocation or modern gthread
entry points. This avoids recursion when the thread bridge itself uses atomics
during initialization. One lock also avoids address hashing and virtual-alias
assumptions. It deliberately favors correctness over parallel throughput for
operations without native hardware support.

## Target policies

- Intel's libatomic uses the upstream i486 baseline selection. Native 1/2/4
  byte compare-and-swap interoperates with the compiler's ordinary aligned
  loads/stores. The library requires an i486 or newer CPU. Eight-byte and
  larger operations use the native lock fallback; no Pentium cmpxchg8b or
  IFUNC assumption is added.
- M68k retains native compare-and-swap at 1/2/4 bytes. Larger objects use the
  shared fallback. Execution is verified on the 68040 test guest.
- SPARC v8 has no compare-and-swap instruction. General atomic operations
  are emitted out of line, so stores, loads and compare-and-swap share the
  same fallback protocol. An inline store cannot safely interoperate with a
  compare-and-swap implemented as a locked load followed by a store. The
  compiler enforces this policy, rather than relying on application flags.
  Dedicated atomic_flag operations retain native ldstub expansion. Libatomic
  does not inherit the upstream SPARC v9 CPU bump.
- HPPA retains the original PA sync helper algorithms with native NeXT lock
  and assembler adapters. Libatomic enables those helpers rather than mixing
  a second scalar locking protocol with them. Eight-byte helper loads and
  stores use hardware doubleword floating-point transfers to avoid tearing.
  Those helpers use locks, so lock-free queries must return false.

GCC originally treated legacy synchronization libcalls as lock-free when
folding the built-in query, even though the NeXT PA implementation uses a
lock. A target hook now distinguishes operation availability from lock-free
progress. It preserves the existing default on other targets and returns false
for the NeXT PA helpers. The library also avoids treating those helper
loads/stores as evidence of lock-free progress.

## Validation and limits

tests/cxx-runtime/atomics.cc checks 1/2/4/8-byte scalar operations, pointers,
bools, generic aggregates and object-size queries. Four concurrent workers
collectively perform 4,000 updates to each shared 32-bit, 64-bit and 12-byte
aggregate object. Every observed aggregate must preserve its field
relationships. The workers also check atomic_flag mutual exclusion. The suite
includes explicit negative lock-free assertions on SPARC and HPPA.

Actual guest execution passes 52 checks on NEXTSTEP 3.3 Intel and m68k, and
Intel OPENSTEP 4.2. SPARC and corrected HPPA pass 56 checks, including
explicit negative lock-free queries at all four scalar sizes. These are
focused regressions, not exhaustive C++ conformance or a memory-model proof.

Locks are process-local. Process-shared mapped atomic objects and signal
handler access to lock-based atomics are not supported. HPPA's byte-sized
atomic_flag currently uses the legacy locked helper, so it does not provide
the standard's unconditional lock-free progress guarantee. Mutual exclusion
works, but this limitation must remain explicit. Native lock-free byte
test-and-set is not provided by PA's aligned word-sized ldcw instruction.
