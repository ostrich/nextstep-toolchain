# Toolchain development workflow

The public workflow is ordinary compiler commands and nextpkg. Building from
source uses tools/build-local-release.py as described in the root README.
Application sources and patches belong in their own projects or the optional
workspace directory, not in this toolchain repository.

## Maintained inputs

- sources.lock.json and patches/series pin GCC and its ordered target patches.
- toolchain/sources.json, toolchain/patches and toolchain/compat maintain the
  classic Mach-O tools and Linux portability changes.
- toolchain/fixed-vm maintains the historical shared-library constructor.
- runtime/ maintains compiler-specific target runtime adaptations.
- nextstepcompat/ maintains general C/POSIX compatibility sources and tests.
- src/nextpkg and src/nextufs contain the bundled packaging and SDK readers.
- [tools/](../tools/README.md) contains build recipes, driver sources and release tools.
- [tests/](../tests/README.md) contains regression checks, guest helpers and qualification fixtures.

Export fixes as ordered patches against pristine pinned sources. Do not rely
on edits in generated upstream trees. Keep SDKs, media, caches and build
products ignored. Record input identities without distributing SDK contents.

## Stage and qualify

Build into a fresh directory and record the toolchain.json manifest used for
testing. Never modify a qualified release in place. For a component-only
update, copy the qualified bundle to a fresh stage and replace only that
component using its build/install helpers. Check the updated manifest and
run relevant regressions against the actual stage.

Compiler changes require exact patch replay, installed-driver checks and
native execution of the affected cases. Header changes require
tests/test-header-order.py and tests/test-sdk-headers.py. Shared-library
changes require constructor, ABI and unchanged-consumer upgrade checks.
The [build guide](cxx-toolchain.md) and [validation scope](validation.md)
describe the available checks.

An optional local installation can use tools/promote-toolchain.py. Promotion
verifies hashes and provenance, copies the stage into install/snapshots and
atomically selects install/current. Existing snapshots remain immutable.
This mechanism is not required to use or distribute the portable bundle.

## Optional guest test tools

Guest-based ABI, SDK, language and assembler checks require an explicit
`--agent-client /path/to/agent-client.py` and guest `--socket`. The supplied
Python transport module must expose `GuestAgent` with the upload, download
and execute methods used by the selected check. It is an external test
transport, not a compiler or package-building dependency. These tools do not
search sibling repositories for a transport.

The RISC runtime and shared-library guest preparers also require
`--risc-preparer /path/to/prepare-validation-cd.py`. Supply the external
validation-CD preparation script matching your test fixtures. Its existing
`--lab`, `--iso`, `--probes`, `--nextufs`, `--extra` and `--argument` interface
must match the preparer's invocation. No particular checkout location is
assumed. `tests/guest/intel33-console.py` similarly requires an explicit
`--console-client /path/to/risc_control.py` exposing `Guest` with `qmp`,
`screen` and `directory`. Inspect each tool's `--help` for its other required
private inputs.

## Create an archive

After qualification, tools/create-release.py compares the stage with the
explicitly supplied tested bundle, checks SDK and guest evidence, refreshes
release metadata, audits the contents and writes the archive and checksum.
Run it with --help for evidence arguments. It neither installs nor uploads
anything. The SDK and workspace are user-owned and never part of a release.
