# Single-byte character support

This backend uses a byte-preserving, stateless encoding. Every byte from
0 through 255 maps to the same numeric wide value. It does not reinterpret
the native character set as Latin-1 or Unicode. Native mbtowc sign-extends
high bytes on the tested system; the adapter deliberately corrects that.

The public ABI retains unsigned 16-bit `wchar_t`. `wint_t` is unsigned 32-bit,
so WEOF is distinct from every wide code unit. `mbstate_t` is a 16-byte
structure with reserved storage. Initialize it with `{0}` and treat its
fields as implementation details. Future encoding support must preserve that
layout or introduce an explicit ABI transition.

## Conversion

The layer supplies mbrtowc, mbrlen, wcrtomb, mbsinit, mbsrtowcs, wcsrtombs,
their bounded-source variants, btowc and wctob. It also corrects the native
mblen, mbtowc, wctomb, mbstowcs and wcstombs interfaces through ns33_ adapters.
Those legacy native entry points are left intact for other applications.
New functions absent from the native library use ordinary C symbol names so
configure link probes can discover them.

- MB_CUR_MAX is one. MB_LEN_MAX remains an upper bound from the SDK/compiler.
- All byte values are valid. A zero input bound returns the restartable
  incomplete-sequence result without changing the output or errno.
- Encoding a wide value above 255 fails with EILSEQ and does not truncate it.
- Null-input/output reset requests obey the respective restartable and legacy
  contracts. There is no shared mutable conversion state in this backend.
- String conversion updates the source pointer on truncation, clears it after
  consuming NUL, and leaves it unchanged for a size-only query. Size queries
  ignore destination capacity. Bounded-source variants honor their input bound.
- On an encoding error, an actual conversion leaves the source at the bad
  wide value; a size-only query leaves the caller's pointer unchanged.

The single-byte backend has only an initial conversion state. Nonzero state
storage is reserved, not a supported way for callers to select an encoding.
Locale selection remains with the native library; no UTF-8 or new locale is
advertised. A later UTF-8 backend also needs consistent locale selection and
an explicit policy for characters outside the 16-bit range.

## Classification, strings and width

wctype and the isw* family use the native byte classification tables for
values 0 through 255. iswblank recognizes space and tab. Wider values and
WEOF are not classified. Case conversion uses native mappings for byte
values and leaves other values unchanged. wctrans supports tolower/toupper.

Wide string and memory operations work on code units, independently of
whether those units can be encoded. C-locale collation is lexical ordering.
wcwidth reports zero for NUL, one for native printable byte characters and
minus one otherwise. wcswidth stops at NUL or its bound and rejects strings
containing nonprintable/unrepresentable characters. No combining-character,
East Asian width or terminal-rendering support is implied.

The headers intentionally do not declare unimplemented wide stream I/O,
formatted wide scanning/printing or wide numeric parsing. Their presence
must not make configuration probes infer a complete wide C library.

## Tests

The standalone test checks every byte and every 16-bit wide value, conversion
and source bounds, reset/error behavior, query non-mutation, canaries,
classification descriptors, WEOF, widths, string functions and overlapping
memory moves. The host runner uses a private test namespace and -fshort-wchar
to avoid calling the host's incompatible wide library. It enables ASan/UBSan.
The same C test runs on the actual targets and additionally checks the normal
header mappings for legacy native functions.
