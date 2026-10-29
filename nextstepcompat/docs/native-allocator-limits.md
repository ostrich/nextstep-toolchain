# Native allocator large-request failure

Status: diagnosed on Intel OPENSTEP. A checked adapter and focused tests
pass on NIHS and Intel OPENSTEP, using optimized static and shared builds.
A native malloc(1073741824) call reproducibly faults inside the original
zone allocator. Disassembly shows sizes shifted by two bits and two low
flag bits, consistent with a 30-bit size field. This is a native allocator
limit, rather than a failure of the calling application or compiler.

The old NeXTSrc libc-34.1 allocator has a size:30 header. The newer public
Darwin-0.3 source retains that field and the related zone allocation/rounding
logic. Its Git blob was independently verified:

- Repository: https://github.com/evolver56k/Darwin-0.3
- Revision: 745305afd074437bb660bcf02146a2754eeef5ae
- File: Libc-1/gen.subproj/malloc.c
- Blob: 88cb0e5d941f547419549c94fff4f6b9b509f0ee

The source is a guide, not a substitute for the original target disassembly.
No original runtime binary has been patched or redistributed.

## Checked adapter

The stdlib overlay directs newly compiled malloc/calloc/realloc calls to
ns33_malloc/ns33_calloc/ns33_realloc. Shared ABI minor 5 appends three slots;
existing occupied slots retain their positions. Existing native callers are
not interposed or patched.

The default external zone has a 30-bit header size. The guard reserves four
header bytes, up to seven alignment bytes (the NIHS maximum alignment is
eight), a 12-byte dummy block, eight deadwood bytes, page_size-1 VM rounding
bytes, and eight bytes for joining regions. Requests above
0x3fffffff - 39 - (page_size - 1) fail with ENOMEM before native allocation.
This is a conservative representability bound, not a promise that a request
below it fits available memory. The adapter reads the native vm_page_size
variable used by the allocator, avoiding a syscall on every allocation.
It does not expose or wrap arbitrary nested NXZone allocation APIs.

calloc checks multiplication before allocating and clearing. realloc retains
the original object on failure. The reference native realloc has a separate
failure path that copies through a NULL allocation, so the adapter uses
native malloc_size, checked malloc, copy and native free. Shrinks stay in
place; growth may copy where native realloc might have extended in place.
Zero-size requests retain the native malloc(0) policy. Returned objects remain
compatible with native free and malloc_size. No private representation or
replacement allocator is introduced.

allocator-guards.c supplies controlled native operations and checks overflow,
rounding, ordinary/zero requests, missing errno, failure preservation and
successful realloc. allocation-native.c exercises public names and actual
native pointer interoperability in the guests. allocation-faults.c retains
the existing imported strdup/strndup/vasprintf failure checks.

## Validation

Host boundary tests pass 180 checks with address/undefined sanitizers. Static
and shared native probes pass on all four NEXTSTEP 3.3 targets and Intel
OPENSTEP, including pointer interoperability, failure preservation and injected
errors. The NIHS checks preserve all prior shared export addresses and pass
C/C++ header-order and SDK-header checks.

These results do not certify every native allocator behavior or protect
against heap corruption caused by invalid application pointers. Tests must
separate representability errors from resource-dependent allocation failures.
