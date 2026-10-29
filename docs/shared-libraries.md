# Shared libraries on NEXTSTEP

The Linux-hosted toolchain can build fixed-address Mach-O shared libraries for
all four NEXTSTEP 3.3 architectures. Intel OPENSTEP 4.2 can run the same
binaries, subject to the system APIs used. All compilation, library
construction and packaging runs on Linux. Guests are used for runtime and
installation validation.

## Build the tools

After building the pinned modern cctools host tools:

```sh
python3 tools/build-shared-tools.py
python3 tools/stage-shared-support.py --output work/stage/shared-support
```

The constructor is mkshlib from the pinned cctools-622.9 release. It uses our
modern cctools support library, assemblers and linker. Apple removed mkshlib
from later releases, so its source pin and Linux patches are tracked
separately under toolchain/fixed-vm. No original guest executable is used. The
full installer also includes these tools through cxx-build-set.json. Test a
stage before promoting it using the canonical workflow.

## Create and consume a library

Fixed-address libraries do not require PIC. Describe the stable ABI in a JSON
specification, then compile its sources with that same export specification:

```json
{
  "install_name": "/usr/local/lib/libexample.1.shlib",
  "minor_version": 1,
  "canonical_entries": true,
  "addresses": {"text": "0x28200000", "data": "0x28300000"},
  "segment_reservation": "0x00100000",
  "exports": ["_example_function", null, null]
}
```

Choose nonoverlapping addresses for each library after checking the target
system and all dependency reservations. Example addresses are illustrative,
not a public allocation registry. Keep install names, addresses, signatures,
public data layouts and occupied branch slots stable. Compatible additions
fill reserved slots and increase minor_version. Breaking changes need a new
major library name and distinct reservations. Never renumber existing exports.

```sh
nextstep-gcc --sdk /path/to/sdk33 --shared-exports shared.json -O2 \
  -arch m68k -arch i386 -arch hppa -arch sparc -c example.c -o example.o
nextstep-shlib --sdk /path/to/sdk33 --spec shared.json \
  --output libexample.1.shlib --import-library libexample.a \
  --build-record shared-build.json example.o
nextstep-gcc --sdk /path/to/sdk33 -O2 main.c -L. -lexample -o example
```

Fat objects produce fat runtimes and import archives; repeat --arch to
restrict targets. The runtime .shlib is installed on the guest with execute
permission (0755). The .a is a small import archive used at link time, not a
static copy of the library. The consumer contains an LC_LOADFVMLIB reference
and absolute branch-table entry addresses. Normal -L/-l linking consumes these
archives without special flags; the driver's -static linker mode still permits
fixed-VM imports.

Canonical entries give callback tables, returned function pointers and
external callers the same public address. The compiler isolates function
definitions before assembly while retaining public references. The constructor
discovers branch addresses, resolves those references, verifies the final
addresses and hides implementation-body symbols from the runtime and import
exports. Ordinary unprepared objects are rejected in this mode. The
implementation-body prefix _ns33_shlib_body is reserved. Original C sources
need no definition renaming.

Final import archives have normalized timestamps, ownership and permissions,
including copied legacy members. The NIHS regression independently replays
construction and requires byte-identical runtime and import outputs.

Pass --dependency /path/to/libdependency.a to nextstep-shlib for each shared
dependency. Its function addresses are resolved without embedding its code;
the resulting import archive carries the transitive runtime closure. Consumers
still link only the top-level import archive. Imports reserve the full text
and data ABI ranges, including unused space, so future compatible growth does
not invalidate earlier collision checks. Conflicting identities, overlapping
ranges and parent cycles are rejected. See [dependency construction and
validation](shared-dependencies.md).

## Scope and remaining work

This path supports C libraries with explicitly exported functions and declared
shared dependencies. Undeclared non-system dependencies are rejected. Archive
inputs use normal member selection, seeded with every public function and data
export. Dependency symbols are resolved before searching those inputs, so a
convenience archive's duplicate dependency members are not embedded in the new
runtime. Direct object inputs are always included; pass them explicitly when
an otherwise unreferenced initializer is required. Native addresses are
resolved from that target SDK's libsys_s import archive, including its
indirect aliases. The system shared runtime is loaded through the executable's
normal startup/import archive.

Canonical libraries declare the shared NextStepCompat import when they need
its APIs. This prevents unresolved public references from pulling duplicate
static implementations during construction. Compiler helpers remain private.
The historical noncanonical mode can still include NextStepCompat privately.
The shared NextStepCompat build recipe is nextstepcompat/build-shared.py and
its stable function slots and addresses are in nextstepcompat/shared.json.
Package the runtime for guests and the import archive for developers.
Initialized public data exports are supported as described below. Shared C++
runtimes/initialization still need further work and validation. This is not a
claim that the OPENSTEP dylib recipes or every legacy dependency now work
unchanged. Shared packaging remains the policy; unsupported cases are explicit
toolchain tasks rather than automatic static fallbacks.

The wrapper checks export presence/type, segment reservations and unresolved
symbols. It records SDK, toolchain, input and output hashes. Promotion
verifies the pinned constructor, patches, wrappers and all installed file
hashes.

## Regression checks

Run the host constructor checks against a staged candidate:

```sh
python3 tests/shared-libraries/test-driver.py \
  --toolchain work/stage/shared-support --sdk /path/to/sdk33
```

check-abi.py additionally compares old/new import archives and the actual
consumer load commands. Runtime tests must also exercise an unchanged consumer
across a compatible upgrade and explicitly reject missing or incompatible
dependencies.

## Public data and function identity

The constructor supports `data_exports`, with explicit `name`, `kind` (`data`
or `const`) and power-of-two `slot_size` entries. An entry without a name
reserves a slot. Writable exports currently require initialized
`__DATA,__data` storage. Public zero-fill exports are not yet supported. Const
exports use a separate read-only `__ABI` segment at the midpoint of the
reserved text range. Each ABI slot must accommodate the entire input atom,
including its trailing padding. Maintaining addresses does not replace
preserving the public object's type and layout.

Cctools patch 0004 adds `.symbol_align <exponent>` to section order files. It
aligns only the next explicitly ordered atom and preserves the historical
input alignment behavior for other atoms, including private data. This avoids
public addresses changing when unrelated private arrays increase the merged
section's alignment. Existing `.section_offset` and `.section_align`
directives cannot do this because normal atom placement subsequently reapplies
the input phase.

## Compatible dependencies and startup

Import archives carry the transitive runtime closure. When several branches
require different compatible minors, the consumer retains the highest version
floor. Runtime identities, header addresses and complete reservations must
agree. Conflicting exports, mappings, cycles and basenames are errors.
Executable links normalize import closures in private copies without changing
caller archives. Equal absolute symbols coalesce only within matching fixed-VM
modules; ordinary duplicate definitions still fail.

Classic startup tables __fvmlib_init0/__fvmlib_init1 must survive dead
stripping. The restored linker preserves their initialization atoms. Intel and
m68k support -dead_strip; HPPA and SPARC reject it because their relocation
walkers do not provide the necessary liveness analysis. Optimized compilation
remains supported on every target.

## Mixed data slots

Each public data slot is aligned to its power-of-two size within its writable
or read-only range. A larger slot after a smaller one can require padding.
Slot size, order, address and object layout are all part of the ABI. Private
data growth must not change public addresses. The .symbol_align linker order
file directive aligns the next explicitly ordered atom without changing
unrelated input alignment.

## Regression coverage

The tests/shared-libraries fixtures cover constructor checks, deterministic
replay, a diamond dependency graph, full reservations, mixed data slots,
canonical function-pointer identity, dependency-order independence and
unchanged-consumer upgrades. Native NEXTSTEP 3.3 execution has covered all
four architectures; Intel OPENSTEP has additional integration coverage. The
-all_load closure variants have Intel OPENSTEP execution coverage only. These
tests do not qualify arbitrary new library specifications or shared C++
initialization. See [release validation](validation.md).
