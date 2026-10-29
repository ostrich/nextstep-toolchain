# Binary64 math support

These pristine files come from the pinned musl 1.2.6 release. COPYRIGHT retains
its licensing terms; the log2 implementation and tables also carry Arm's MIT
notice. The build verifies every source hash, replays the adapter patch, and
compiles the resulting sources separately from the original system library.

The adapters namespace fmin, fmax, log2 and the private log2 table. The log2
polynomial and coefficients are unchanged. A small support header supplies
binary64 bit casts, explicit double evaluation and the two exceptional-result
helpers. Those helpers preserve IEEE invalid/divide-by-zero behavior and add
EDOM/ERANGE for POSIX domain and pole errors. NaNs propagate without assigning
a domain error merely because the input is NaN. No long-double API is implied.

fmin and fmax retain musl's handling of NaNs and signed zero. Public math.h
also exposes the native BSD math functions hidden by the SDK's POSIX feature
mode. These native declarations do not substitute approximate implementations.

The math-clock regression checks all exactly representable powers of two,
high-precision generated numerical vectors, NaNs, infinities, signed zeros and
error reporting. Its realtime checks cover representation, bracketing with the
native clock, unsupported clock IDs and preservation of the destination on
failure. Successful host results do not establish native numerical behavior;
run the same binaries on the supported target systems.
