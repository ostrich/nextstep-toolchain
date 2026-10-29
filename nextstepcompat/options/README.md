# Option parsing and rounding reference sources

Pristine sources are pinned to the released musl 1.2.6 archive. The patches
record the adapters maintained in src/. getopt state is namespaced and shared
between getopt, getopt_long and getopt_long_only; it does not alias the original
system getopt globals. Diagnostics use native stdio and the C locale. Parsing
uses NextStepCompat's existing single-byte multibyte functions.

Public variables use stable data slots in the shared ABI. Applications should
include getopt.h or unistd.h and use one option parser family consistently.
The original libc and previously linked executables are unchanged.

The round and floorf algorithms are musl's IEEE double/float implementations with a small native
support header substitution. See COPYRIGHT for musl licensing.
