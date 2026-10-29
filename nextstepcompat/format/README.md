# Formatted output

The baseline is src/stdio/vfprintf.c from the official musl 1.2.5 release.
The original source and COPYRIGHT are retained here. sources.json pins the
release archive and this file's hash. The build copies the baseline privately
and applies 0001-nextstep-bounded-output.patch without fuzz.

The first patch replaces musl's internal FILE output with a bounded buffer, provides
snprintf/vsnprintf entry points, and uses NextStepCompat's single-byte wctomb for wide character conversion.
Integer and floating conversion retain musl's parser and rounding logic. A local exact power-of-two decomposition avoids narrowing an
extended-precision value through NEXTSTEP's double-only frexp. Conversion uses
the C/POSIX locale, which is the locale supported by this runtime.

This is not an installation of musl or a replacement for the original libc.
The compatibility archive provides functions absent from the original system.
libstdc++ uses the bounded formatter for locale output and long-double
conversion because the original printf family does not read long double
arguments correctly.

The formatting test covers integer widths, positional arguments, truncation,
zero-size buffers, rounding, exponent extremes and 200 deterministic extended
precision cases. The Intel host and guest use the same 80-bit representation.
Hexadecimal formatting may have a different normalization while representing
the same value; compare that case numerically. Other outputs are compared
exactly. The runtime startup object must establish extended x87 precision
before arithmetic or user constructors; merely using 80-bit storage does not
change NEXTSTEP's initial 53-bit arithmetic mode.

Allocating asprintf/vasprintf entry points use the unmodified public-interface
implementations from musl 1.2.6 in allocation/. Their separate pin and license
are retained there. Both use the same bounded formatter, including its
extended-precision support, rather than the native sprintf implementation.
This is important for applications whose own allocating fallback delegates
long-double output back to native stdio.
Their malloc calls use a private adapter so allocation failures set ENOMEM
even when the native allocator leaves errno unchanged.

The follow-on stream-output patch exposes printf/fprintf and their va_list
variants through ns33_ adapters. It emits bounded chunks through native
fwrite, retaining the native FILE ABI and buffering. It neither allocates a
complete formatted string nor flushes after every call. The native bridge
marks a stream error when a write fails and returns the required character
count on success. Native sprintf/vsprintf are not replaced by this patch.

The public fwrite adapter and formatter share the same write bridge. Native
fseek clears direction flags on update streams, but native line-buffered
fwrite can report success without reestablishing write mode. A later fflush
then drops the write. The adapter establishes write mode and reconciles any
retained read buffer, preserving native element counts and buffering. It also
sets the error indicator for rejected or short writes. Zero-size writes return
zero without changing stream state. Original symbols remain available to
pre-existing binaries.

ungetc reserves room when unread input begins at the native buffer's start.
It preserves unread bytes, never frees caller-owned setvbuf memory, supports
unsigned-byte results and clears EOF after successful pushback. Any allocated
replacement buffer is marked for native fclose to release. Native fseek and
other stream operations continue to operate on the same FILE object.
The buffer-growth path can fail with ENOMEM while preserving unread data;
the legacy FILE layout has no separate preallocated pushback reserve. This
is an explicit limit of this bridge, not a complete replacement stdio layer.
Repeated EOF reads can leave the native count negative; the adapter normalizes
that empty state before requesting pushback from the native implementation.
