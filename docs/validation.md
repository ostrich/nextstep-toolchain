# Release validation

The Linux x86-64 bundle was built locally from the pinned sources and maintained
patchsets. It uses optimized compilers and target runtimes. The source-build
entry point completed with an SDK whose directory contained spaces.

The append-stream compatibility wrappers pass 420 native checks on each of
the four targets in both static and shared builds. Coverage includes append
after truncation or seeking, binary update modes, descriptor duplication,
reopening, access checks and descriptor ownership on failure. Native fdopen
requires binary-mode normalization, and native append streams require
O_APPEND to maintain append semantics after a truncate or seek. The shared
runtime preserves existing function slots and adds these wrappers at minor
version 22. Compiler and host-tool binaries are unchanged from the preceding
qualified bundle; this component update did not repeat the compiler campaigns.

| Check | Result |
| --- | --- |
| C, C++, Objective-C and Objective-C++ on NEXTSTEP 3.3 Intel, 68k, HPPA and SPARC | Passed |
| C++ threads, atomic increments and exception handling on all four targets | Passed |
| Host package creation, native installation, execution, receipt verification and removal | Passed on Intel |
| Developer-CD extraction, four-target compile/link checks, refusal to overwrite an SDK, invalid-media cleanup | Passed |
| Relocation to a directory with spaces and the example build/package workflow | Passed |
| Four-target linking with system 32-bit host libraries hidden | Passed |
| Package-builder tests and four-target C build | Passed; 24 package tests |
| Four-target AppKit application linking | Passed; GUI execution not covered by this check |
| Full GCC patch replay and untouched upstream source verification | Passed |
| Archive hashes, private build paths, SDK exclusion and empty user directories | Passed |

Native tests ran on disposable guests. Each guest halted through its operating
system and passed a stopped filesystem check. Package testing exercised the
native command-line installation path and receipt-based removal, not a separate
visual Installer walkthrough.

These are toolchain release checks, not exhaustive compiler conformance or a
promise that an arbitrary application will compile unchanged. Programs still
need target-side testing. Physical hardware and a range of Linux distributions
were not separately qualified. The host kernel needs 32-bit x86 execution support.

The release records its source commit and a code fingerprint in
share/distribution.json. Its code matches the guest-tested bundle, comparing
archive members independently of archive-header timestamps and ownership.

## Compiler regression coverage

The maintained compiler patchset also repairs HPPA complex-call expansion and
nested-function trampolines, Intel dynamic stack alignment, and 68k copysign and
single-precision multiplication. The runtime recipe includes upstream libgcc
complex multiplication and division helpers. The public driver preserves
separate option arguments and requested compiler dumps and saved intermediates,
including distinct names for architectures in fat builds.

These changes passed focused native tests on all four targets, C++ ABI,
exception/thread checks, 25 driver-output cases and 16 header-order cases before
export. Broad execution covered Intel, HPPA and SPARC; the 68k replay covered
changed executables, the full runnable IEEE/builtin batches and additional
unchanged cases. It was not a complete rerun of every unchanged 68k baseline
program. Stack-budget controls distinguish resource exhaustion from compiler
failures. Existing public C99 API and classic assembler limitations remain.

The exported patches replay without offsets or fuzz and reproduce the qualified
compiler source files. Emulator fixes used during testing are maintained
separately and are not included here.

The distributed compilers and runtimes passed the native regressions above.
Subsequent package-builder and documentation changes preserve those compiler
and runtime bytes. The current builder passes 24 host tests and produces a
byte-identical copy of the example package qualified through native installation,
execution, receipt verification and removal. Documentation-only updates do not
constitute additional compiler or guest qualification.
