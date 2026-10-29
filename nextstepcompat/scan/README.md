# Formatted input

The scanner uses pristine vfscanf, intscan, floatscan and shgetc sources from
musl 1.2.6. sources.json pins the release, original paths and file hashes.
The adaptation patch applies without fuzz to private build copies.

A private scanner structure supplies musl's field widths, byte counts and
lookahead without changing the public NeXT FILE layout. File input goes
through native getc; pending lookahead returns through the compatibility
ungetc adapter. String input is bounded by the terminating NUL. No temporary
files, global input state or fake native FILE objects are used.

The integer and floating algorithms retain musl's parsing and rounding
logic. Floating input shares the existing exact binary scaling helpers with
the strtod family, avoiding narrowing long double through native double-only
math functions. Integer widths, assignment suppression, scansets, positional
arguments, C99 numeric formats and single-byte wide conversions use the same
core for sscanf/fscanf/scanf and their va_list variants.

Headers select ns33_ public adapters while retaining the original native
symbols. These are C/POSIX-locale interfaces, not Unicode locale support or
wide-stream I/O. Shared FILE access has the native library's synchronization
limits; this component does not add flockfile or a new stdio locking system.
The internal scanner functions are not a public extension API.
