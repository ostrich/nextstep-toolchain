# Binary64 math and realtime clock qualification

The musl 1.2.6 fmin, fmax and log2 adapters and the gettimeofday-based
realtime clock passed the focused regression on Intel, m68k, HPPA and SPARC
NEXTSTEP 3.3. Each target executed all 2,390 checks against shared ABI minor
21. The suite covers signed zeros, NaNs, infinities, log2 domain/pole errors,
every binary64 power of two, 264 high-precision numerical vectors and clock
error and representation rules. Clock bracketing assumes no administrative
wall-clock change during the short test.

A host ASan/UBSan run passed the same checks, an injected gettimeofday failure
and a comparison of one million positive finite double bit patterns against
host log2. The differential's maximum discrepancy was one ULP. The committed
Decimal reference table is independently generated at 160-digit precision; the
host library is a supplementary reference, not the sole numerical oracle.

All four targets also ran previously built threading and TLS consumers against
the new shared runtime. The existing 279 function slots and data specification
are preserved; four function entries are appended. C and C++ header probes
passed on NIHS, as did the canonical public-driver header-order test. These
checks cover the new math/time declarations and existing include ordering.

The first m68k power-of-two test generated subnormal inputs with native ldexp
and failed 52 cases. The corrected test constructs exact binary64 inputs from
bits and passes every exponent. This isolates log2 qualification from an
unrelated native input-generation dependency; it does not qualify ldexp.

All four guests reached native halt, their results were collected afterward,
and all five guest filesystem checks passed. OPENSTEP 4.2 execution has not
been checked for these additions.

Reproduce the component build with build.py and build-shared.py. Run
math-clock-host.py --sanitize for host checks and build-math-clock.py --shared
for the fat native regression. The helper arguments and test contracts are in
[the tests README](../tests/README.md).
