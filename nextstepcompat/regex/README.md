# POSIX regular expressions

Pinned musl 1.2.6/TRE sources provide regcomp, regexec, regerror and regfree.
Original files, hashes and license notices remain separate from the adaptation
patch. Public interfaces use standard POSIX symbols and have their own regex_t ABI;
they do not reuse the native SDK's unrelated re_compile/re_match interface.

The adaptation preserves native 16-bit wchar_t, bounds the internal character
range accordingly, namespaces allocator symbols and removes musl-internal
ELF visibility and locale-message translation dependencies. Matching uses
NextStepCompat's single-byte character layer and native classification tables.
Error descriptions are English. No UTF-8 or locale service is introduced.

A second adaptation supports single-byte collating elements and equivalence
classes in bracket expressions for the C/POSIX locale. Collating elements can
be range endpoints; equivalence classes cannot. Empty and multibyte collating
names are rejected with REG_ECOLLATE. This does not implement locale-specific
collation or multicharacter collating elements.

The public include/regex.h is derived from the pinned upstream header with
native type declarations. The unmodified upstream header
is retained here as upstream-regex.h for comparison.

Build and run tests/regex.c as described in tests/README.md. It exercises
matching, flags, capture offsets, invalid patterns, error formatting and
repeated allocation/free. A successful library build alone does not establish
application correctness or full POSIX conformance. See the component test
guide for native regression entry points.

RE_DUP_MAX is exposed by this regex header as 255, matching the engine's
repetition bound. Internal character-class names have a 14-byte bound.
Binary distributions must retain both COPYRIGHT and TRE-LICENSE.txt.

The public POSIX entry points are new symbols, so they use their standard
names. Only private allocator symbols use the ns33_ namespace. This also
allows ordinary Autoconf link probes to discover the functions without
including regex.h. Existing native legacy functions retain their own ABI.
