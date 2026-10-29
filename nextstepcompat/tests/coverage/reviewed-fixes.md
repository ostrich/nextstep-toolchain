# Coverage-driven libc fixes

The first audit's confirmed failures are corrected in NextStepCompat. This
follow-up keeps the original [baseline](initial-coverage.md) for comparison.
It does not claim complete C99 or POSIX conformance.

## Implementations

- strstr uses the unchanged musl 1.2.6 search implementation.
- strtol/strtoul reuse the existing checked integer converter for native-long
  limits, signs, prefixes, overflow and complete end-pointer consumption.
- sscanf/fscanf/scanf and their va_list variants use pinned musl 1.2.6 scanner
  sources through a private adapter. They retain the native FILE ABI.
- printf/fprintf and their va_list variants use the existing musl formatter,
  emitting bounded chunks through native buffering with correct return counts
  and stream error reporting. Native sprintf/vsprintf are unchanged.
- ungetc preserves unread data at buffer boundaries, handles unsigned bytes,
  clears EOF after success and normalizes a negative count left by repeated
  native EOF reads. Caller-owned buffers are never freed.

Headers select ns33_ adapters, preserving original native symbols. Existing
applications need rebuilding to use these statically linked corrections.
All builds remain optimized. Pristine upstream files, licenses, hashes and
fuzz-free adaptation patches remain with the component.

## Validation

The final compiler bundle passes 648 SDK header/layout checks and 100
installed-driver checks, including fat linking, extracted slices and relocation.
All four libatomic and C++ runtimes were rebuilt with the new header snapshot.

Each NEXTSTEP 3.3 target (Intel, NeXT 68k, SPARC and HPPA) passes the same
19 compatibility/C++ programs. They include eight upstream programs, the
1,330-check reduced regression program, existing smoke/character/regex/
allocation/signal/FIFO/group tests, and three representative C++ programs.
That is 76 successful compatibility/C++ program runs across the four targets.
Native-only controls still produce the four expected failing programs per
architecture, preserving evidence that the replacements correct real gaps.

The same 19 compatibility/C++ programs also pass on Intel OPENSTEP 4.2 in the
separate build guest. Temporary test programs and directories were removed.
The production guest was not used.

Host checks pass 22,512 integer comparisons, including 32-bit long against
multilib libc, and 30,096 floating-conversion comparisons. Five selected
string/scanning/formatting programs pass with address/undefined-behavior
sanitizers. Seven collector checks reject incomplete or contradictory logs.

All four disposable NEXTSTEP guests reached native shutdown before their
emulators were stopped. Offline read-only filesystem checks pass for all
seven images. Exact logs are hashed in fixes-triage.json; the generated
[follow-up matrix](post-fixes-coverage.md) separates build and behavior results.

## Diagnosis and test boundaries

NeXTSrc and Darwin 0.3 were references, not assumed copies of the running
library. Darwin's newer BSD FILE has a separate pushback reserve, so its
internals cannot be substituted into the older NeXT structure. The actual
NEXTSTEP 3.3 Intel ungetc instructions were inspected: the shared-library
entry branches to an implementation that rejects a nonzero count when its
cursor is at the buffer beginning. Reduced guest tests demonstrate the
negative count after repeated EOF reads on all four targets.

The first targeted run exposed the additional EOF/error-state cases. A later
C++ fixture initially received no required scratch-directory argument; that
was a harness error, corrected by recording explicit per-program arguments.
The corrected batch passes. Earlier failed runs and their original logs are
retained, rather than relabeled as library failures or successful tests.

Mixed BSD string tests remain build-blocked by strlcpy/strlcat. strftime is
blocked by setenv and also has host format-policy differences. Those programs
are not counted as passing. The stdin scanf/vscanf forwarding entry points
build and link, but are not directly exercised by this guest batch. The
character model remains single-byte; wide stream I/O is not supplied.

Pushback buffer growth can fail with ENOMEM while preserving unread data.
The legacy FILE layout has no separate preallocated pushback reserve. Native
stream synchronization limits remain; this is not a replacement stdio layer.
Remaining missing interfaces stay in the coverage ledger for later batches.
