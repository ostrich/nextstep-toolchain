# C99 trunc

The NEXTSTEP 3.3 system library does not export trunc. NextStepCompat supplies the reusable C99 API.
The implementation clears fractional bits of an IEEE binary64 double without
using the active floating-point rounding mode. It preserves signed zero,
infinities and quiet NaN payloads. C99 permits trunc to omit raising inexact;
no inexact-flag behavior is promised here. This is not a long-double API.

All four NIHS targets store double as binary64. The implementation uses a
64-bit integer view, rather than assuming a host byte order or converting
large values to a target integer. Values at and above 2^52 are already integral.

The regression suite has 26 bit-exact cases covering both signs, subnormals,
near-one values, exponent boundaries, infinities and quiet NaNs. Another 4,096
checks compare exactly represented fractional values with native floor/ceil.
Intel OPENSTEP and all four NEXTSTEP 3.3 targets passed all 4,122 checks,
including shared runtime execution. Older thread-key and LZO consumers ran
against the new minor version. All 161 existing function addresses stayed
unchanged. Each test guest completed native shutdown; seven filesystem checks
passed.

A separate deterministic host test compares one million bit patterns against
host libm trunc, quieting signaling NaNs before the call. All comparisons
passed. This host check does not replace target execution.
