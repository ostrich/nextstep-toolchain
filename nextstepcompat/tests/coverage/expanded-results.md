# Expanded NextStepCompat audit

Verified 2026-10-17 with optimized four-target builds and isolated guests.
The canonical implementation is the nextstepcompat source directory, not
a generated compiler build directory.

## Results

| Environment | Compatibility and C++ programs | New focused assertions |
| --- | ---: | ---: |
| NEXTSTEP 3.3 Intel | 28 passed | 127,836 passed |
| NEXTSTEP 3.3 NeXT 68k | 28 passed | 127,836 passed |
| NEXTSTEP 3.3 SPARC | 28 passed | 127,836 passed |
| NEXTSTEP 3.3 HPPA | 28 passed | 127,836 passed |
| OPENSTEP 4.2 Intel | 28 passed | 127,836 passed |

The assertion counts cover the new memory, stdio, portable API, environment,
calendar and fault-injection programs. Existing upstream cases and library/C++
regressions also pass and are additional to these counts.

The four NEXTSTEP environments launched concurrently. Per-target host start
and observed native-halt timestamps are recorded in parallel-execution.json.
Each ran 38 programs: 28 compatibility/C++ programs and ten native controls.
Native defects remain visible as failing controls; they are not counted as
compatibility passes. All release guests reached verified native halt states.
Read-only offline checks passed for all seven filesystem images. OPENSTEP
execution used the dedicated build guest; production systems were unchanged.

## String and memory coverage

The new string_iso selection preserves every C assertion from the pinned
libc-test string program and omits only its trailing BSD strlcpy/strlcat
block. The pristine mixed program remains scheduled separately and blocked
on those BSD extensions. No upstream input was edited.

The additional memory program checks zero lengths, alignments, overlapping
moves, bounds, all byte values, string termination and tokenization. It
exposed native unsigned-byte ordering defects in strcmp/strncmp on Intel,
m68k and SPARC, and memcmp on m68k/SPARC. Namespaced, pristine musl 1.2.6
implementations correct them. HPPA native ordering passes the selected cases.

## Stdio boundaries

Native FILE tests cover full, line and unbuffered modes; stdin scanf/vscanf;
EOF and pushback; seeking and update streams; writes after EOF; element and
character counts; and read-only or closed-descriptor errors.

A reduced line-buffered update-stream case established that native fseek
clears direction flags, while native fwrite can report success without
restoring output mode. A subsequent fflush discards the data. The shared
write bridge now establishes the correct mode and reconciles unread input.
Public fwrite calls and formatted output both use it, preserving native
FILE layout and buffering. Zero-size writes do not change stream state.

## Environment and calendar behavior

setenv and unsetenv share native environ/getenv, copy values and reclaim
only their own replaced strings. Tests cover overwrite policy, repeated
replacement, invalid names, duplicates and external environ replacement.
They do not add thread-safe or signal-safe environment mutation. An exported
pointer table is retained when a caller replaces environ independently.

The previously blocked, unchanged upstream strftime test now passes.
Additional expectations cover 2,497 Gregorian dates spanning a 400-year
cycle, independently generated without host strftime. These establish native
C90 week-number defects as well as missing modern calendar conversions.

Pinned musl 1.2.6 formatting and calendar helpers implement the C/POSIX
locale. Other LC_TIME locales retain the native formatter. Formatting wide
calendar years does not widen native time_t, kernel clocks or mktime limits.
The suite also checks UTC epoch fields, conversion round trips, leap-day
handling, buffer boundaries and difftime. It does not certify all time APIs.

## Portable additions

- strdup, strndup, strnlen and strtok_r use pinned musl 1.2.6 sources.
- getline/getdelim preserve embedded NULs and delimiters, grow caller-owned
  storage, check ssize_t bounds, and report EOF, read and allocation errors.
- strtoimax, strtoumax, imaxabs and imaxdiv reuse the checked integer layer.
  inttypes.h supplies target-appropriate narrow integer format macros.
- Private allocation glue sets ENOMEM for imported strdup/strndup and
  vasprintf calls. Native malloc was observed returning NULL with errno
  unchanged; fault injection verifies the adapter without exhausting guests.

Wide-string maximum-width integer conversions remain unavailable. Existing
single-byte conversion/width, regex, allocation, signal, FIFO and group
regressions remain gates. Unicode locales and wide stream I/O are not added.

## Build and integration

Use the public driver from a qualified bundle. Build records must identify
the compiler patchset as well as the compatibility component; replacing one
does not update the other.

NextStepCompat install.py updates only component headers, four archives and
the bundle integrity manifest, with a backup. Compiler binaries and other
runtimes remain unchanged. Applications must be rebuilt to pick up the static
library corrections.

Host checks include 22,512 integer comparisons, 30,096 sanitized floating
comparisons and three sanitized portable-string/environment programs. A
separate sanitized allocation-failure program passes. Host FILE layout is
different, so stream-adapter validation comes from guest execution. The
portable environment sanitizer run checks memory safety with leak detection
disabled for deliberately retained externally replaced pointer tables.

After installing the component, all 100 installed-driver checks and all
648 SDK header/prototype/layout checks pass. Installed archive/header hashes
match the tested component; unrelated compiler/runtime file hashes are
unchanged.

## Evidence and remaining coverage

The [expanded ledger](expanded-coverage.md), [machine-readable results](expanded-status.json)
and expanded-triage.json retain exact final guest-log hashes. Availability
probes were reused only where interfaces were unchanged; the new public
fwrite provider was re-probed on all four targets. All runnable behavioral
programs were rebuilt with the final library.

The original mixed BSD string test remains blocked independently of the C
selection. Host failures in the upstream integer/strftime programs reflect
reviewed expectation differences and are retained, not treated as an
infallible oracle. Missing, partially supported and untested interfaces stay
distinct. This audit is not complete C99 or POSIX certification.
