# C library and POSIX coverage audit

This audit inventories 171 interfaces and compares the native NEXTSTEP 3.3
library with NextStepCompat on Intel, NeXT 68k, SPARC and HPPA. It is an
initial inventory, not a complete standards checklist or conformance claim.

The baseline is ISO C99 library functionality, including the earlier C
interfaces it retains, plus selected POSIX.1-2008 application interfaces.
C95/C99 labels identify the wide-character library family. GNU/BSD extensions
can be investigated separately; they are not automatically requirements.

The [initial results](initial-coverage.md) and [interface classifications](initial-status.json)
record the first completed four-target batch. Reviewed observations and the
next implementation batches are in triage.json.

## Build and report

Run these commands from this directory. Use a source-aligned installed compiler bundle. SDK files remain external.
Choose a new output directory for each build snapshot:

```sh
python3 audit.py --toolchain /path/to/toolchain --sdk /path/to/sdk33 \
  --output /path/to/audit --jobs 8
python3 add-regressions.py --toolchain /path/to/toolchain --sdk /path/to/sdk33 \
  --output /path/to/audit
python3 finish.py --toolchain /path/to/toolchain --sdk /path/to/sdk33 \
  --output /path/to/audit
```

The output contains build-results.json, results.json, coverage.md, individual
compiler/linker diagnostics, host controls, target test executables and a
bounded api-batch executable for each architecture. Both modes use -O2 and
-fno-builtin. The native mode excludes NextStepCompat headers and libraries;
it retains GCC support and the SDK's existing syntax repairs. The compat
mode uses the installed bundle's normal headers and runtime selection.
Neither mode changes the original SDK or installed compiler.
The audit rejects stale compiler patch snapshots by default. Use
--allow-stale-toolchain only for an intentional historical comparison;
otherwise known compiler defects can masquerade as libc failures.

Declaration probes require an addressable function declaration. Link probes
force a symbol reference without calling it through a guessed signature.
Where no declaration exists, the raw symbol is checked separately. Successful
linking proves neither the signature nor behavior. Macro presence is recorded
separately: a macro can provide a usable operation without an external symbol.
Compile failures need diagnostic review before classification as missing APIs.

## Execute in disposable guests

prepare-guests.py wraps the existing compiler VM helpers. Its --help lists
the required original media, stopped Previous baseline and tool locations.
It refuses an existing lab directory, copies its inputs and checks staged
executable bytes. It never boots or changes a shared VM. Use a free private
X display for Previous. A partial preparation must be inspected or discarded
before retrying with a new lab directory.

Run the prepared Intel run.py and use tests/guest/intel33-console.py from the
compiler project to identify its single-user prompt. Invoke:

```sh
/bin/sh /api-run.sh
```

The wrapper remounts only its disposable root, records /api-results.txt,
prints the report, syncs and requests a native halt. Previous uses its
prepared launch.py; rc.local runs the batch and records /port-test/results.txt.
SPARC and HPPA use host/qemu/tests/risc/run-validation.py with --root-disk.
Their startup script captures the report in /validation.log on the separate
report disk. Consult those helpers' documentation and the project's existing
UI navigation notes for loader prompts and shutdown evidence.

Each upstream executable runs in a separate process with a 20-second alarm
and core dumps disabled. The parent records exit and signal status. Upstream
failures do not stop later tests. A failed build is not silently substituted
or counted as a passed test. Tests that build successfully are all scheduled.

Collect exact logs after native shutdown and after stopping the emulator.
Do not mutate an image while an emulator owns it. Supply the four logs to
finish.py using repeated --guest-log ARCH=/path/to/log options. The collector
requires every expected result exactly once and validates the summary count.
It records log hashes and distinguishes build failure, untested, runtime
failure and pass. Re-running finish.py without guest logs resets execution
results to untested; preserve each final results.json with its evidence.

## Upstream inputs and adaptations

upstream/ contains pristine selected libc-test files. upstream.lock.json pins
the upstream commit and every file hash; audit.py verifies them before use.
COPYRIGHT and AUTHORS accompany the selection. Original repository and
mirror URLs are in the lock file. There is no upstream release tag assumed.

The original ten upstream programs cover basic strings, strcspn, strstr,
integer/floating conversion, snprintf, sscanf, ungetc, strftime and qsort.
Their pristine bodies are retained. An additional string_iso selection keeps
all original C assertions while omitting the trailing BSD strlcpy/strlcat
block. The original mixed program remains visible as a separate test.
Selected and local sources are snapshotted and checksummed with each build.
The audit supplies these test-only aids:

- harness.c reports errors through vfprintf, avoiding a vsnprintf dependency
  in the error reporter when native vsnprintf itself is unavailable.
- Native qsort's diagnostic-only inttypes.h defines PRIu64 for these targets;
  integer types come from GCC's stdint.h. This is not an installed header or
  evidence that the native SDK has inttypes.h.
- snprintf receives M_PI as a compiler constant because the original SDK
  does not expose it. This is a numeric test fixture, not a math API repair.

Some tests mix standards and extensions. For example, string.c also requires
BSD strlcpy/strlcat; a build failure does not condemn its C90 string functions.
strtol's invalid-base end-pointer expectation also differs on the host libc.
strftime contains expanded-year/format expectations that fail on the host.
Host controls are evidence to investigate, not an infallible reference.

Additional programs cover byte-string boundaries, native FILE transitions,
stdin scanf/vscanf, portable string/line/integer additions, environment
ownership and civil time. Calendar expectations span a complete 400-year
cycle and come from Python integer calendar arithmetic, without host
strftime. The collector includes compatibility-only regression rows rather
than hiding programs that have no native counterpart.

## Classification and implementation policy

Record declarations, symbols, macros and behavior independently. Use these
classifications only with the corresponding evidence:

- Working natively: selected behavior passes; record the tested cases.
- Missing: reviewed header/symbol evidence, accounting for macro alternatives.
- Broken: a reduced valid-input case establishes incorrect required behavior.
- Partially supported: useful behavior exists but the documented contract is
  limited, such as the current single-byte character implementation.
- Kernel-dependent: library-only implementation needs a verified OS primitive.
- Untested: evidence is absent or the test is blocked by another dependency.

Prioritize reusable, self-contained string/numeric adapters, then filesystem
and time interfaces backed by established kernel primitives. Keep application
bugs and compiler/ABI failures out of the library backlog. Do not emulate
missing kernel semantics with misleading success returns. Threads, Unicode
locales, wide stream I/O and a complete libc replacement are outside this
initial audit. Existing NeXT-specific signal, FIFO, groups and character tests
remain separate regression gates.

Run the collector integrity checks with:

```sh
python3 -m unittest discover -s . -p 'test_*.py'
```

## Test a newly rebuilt component

Before staging a complete compiler bundle, audit.py can use --compat-build
/path/to/component-build. This selects the maintained compatibility headers
and newly built library while retaining the installed compiler and startup
support. The build record identifies the separate library snapshot.

Run add-regressions.py with --output, --toolchain, --sdk and --compat-build
before finish.py to add the reduced native negative control and the existing
compatibility smoke, character, regex, allocation, signal, FIFO and groups
regressions, plus line-input and allocation fault injection. The latter
compile the maintained implementations under private injected allocators,
without changing the guest allocator globally. Both native and compatibility
failures remain visible; an
expected native failure is not a successful compatibility result.

The Previous preparation wrapper discards only recognized stale fixture
stdout/stderr/status outputs from its disposable copy to avoid exhausting
the first cylinder group's inodes. Original baseline images remain unchanged.

Batch test metadata may specify up to two ASCII arguments. Tests with required
arguments must record them explicitly; a usage error is a harness failure,
not evidence about the library being tested.

add-cxx.py adds the existing stdlib, numeric and C99 C++ integration gates
against --compat-build, using the installed compiler's other runtimes.
Its stdlib fixture records its two required arguments explicitly.

The four prepared guest environments can be launched concurrently with
separate disks, logs, sockets and a private X display for Previous. Keep
host launch and observed native-halt timestamps for each target. Native halt
must be verified before stopping emulators; completed test output alone is
insufficient. Use the target operating system's shutdown procedure and verify completion.

Later allocation findings
-------------------------

The inventory's malloc/calloc/realloc declaration and link successes are not
allocation-boundary conformance results. A separate allocation test exposed a native
1 GiB allocator crash, independently reproduced from native GDB. The checked
adapter, failure semantics and focused NIHS/OPENSTEP evidence are described
in ../../docs/native-allocator-limits.md. Historical audit results retain
their original scope and should not be read as certifying these boundaries.
