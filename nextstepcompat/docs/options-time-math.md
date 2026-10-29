# Option parsing, time and rounding

Shared minor 15 fills reserved function slots for getopt, getopt_long,
getopt_long_only, localtime_r, gmtime_r, strsignal, stpcpy, strcasestr, floorf,
round and lround. Namespaced optarg/optind/opterr/optopt/optreset occupy stable
256-byte writable data slots, with further slots reserved. Original libc
option state and existing compiled executables are unchanged.

The parser and rounding algorithms are based on the released musl 1.2.6
sources. options/sources.json pins the original files; ordered adaptation
patches reproduce the maintained implementation files during every build.
The integrated compiler supplies the same public headers and static code.

getopt, getopt_long and getopt_long_only share the compatibility option state.
Use one parser family consistently. Diagnostics use native stdio and C-locale
messages; parsing retains the existing single-byte character model. The API is
stateful and is not advertised as reentrant.

The result-buffer time functions serialize calls into the original timezone
implementation, copy the result while holding the lock and leave native
non-reentrant calls with their original thread-safety limitations.
No timezone policy or mid-process TZ-refresh behavior is replaced.

The float-specific floorf algorithm avoids calling native floor through a
float-to-double-to-float adapter: GCC can optimize such a wrapper recursively
back into floorf on targets lacking an inline instruction. The native floor
also fails special-value tests on some targets. Regression callers disable
builtin folding so tests execute the actual library entry points.

lround rounds halfway away from zero and rejects non-finite/out-of-range
results with EDOM and LONG_MIN, rather than relying on an undefined conversion.
Unknown signal numbers return a constant descriptive string. strsignal uses
the native signal-description table for valid signals.

The combined NIHS regression covers 21 option cases, 21 time/string/math
cases, four configuration-open cases and
real owned-process/terminal behavior. Static and shared compatibility paths
are both exercised by the final batch. SDK independence and C/C++ header-order
checks also pass. These are scoped checks rather than general POSIX conformance.
