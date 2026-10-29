# Floating-point parsing

The pristine scanner is `src/internal/floatscan.c` from musl 1.2.5. The
release and source hashes are in sources.json; COPYRIGHT contains its license.
The build copies the scanner and applies the adaptation patch without fuzz.

The adaptation supplies string input without depending on musl FILE internals,
and exposes strtof, strtod and strtold. The original scanner retains its
precision-specific decimal and hexadecimal rounding algorithm. Private binary
scaling and power-of-two remainder helpers preserve extended precision without
calling the original double-only math interfaces or assuming a storage layout.
Parsing uses the C/POSIX locale, matching the runtime locale implementation.

Overflow and underflow report ERANGE. Subnormal results report ERANGE even
when exact, which is permitted for underflow. Invalid input reports EINVAL;
the end pointer still identifies the original input. These two errno choices
can differ from the host libc. Differential tests permit only those documented
differences and compare all result values, signs and consumed lengths.

This supplies functions in the linked compatibility archive. It does not
replace system libc or change independently linked applications.
The public stdlib overlay maps strtod to a private compatibility symbol, since
the original shared-library import archive cannot be overridden by defining
another symbol named strtod. Existing system binaries retain their own parser.
