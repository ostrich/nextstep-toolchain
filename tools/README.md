# Build and release tools

Most users need only the commands in a binary download's bin/ directory.
These scripts maintain the compiler, host tools and release archive.
Run them from the source checkout; use --help for inputs and output paths.

## Normal entry points

| Task | Command |
| --- | --- |
| Build the complete portable bundle | `python3 tools/build-local-release.py --sdk SDK --output NEW_DIRECTORY` |
| Extract a private SDK before bootstrapping | `python3 tools/setup-sdk.py --help` |
| Assemble a bundle from qualified component builds | `python3 tools/assemble-release.py --help` |
| Audit a staged bundle | `python3 tools/check-release.py STAGE` |
| Create the release archive using qualification evidence | `python3 tools/create-release.py --help` |

The [development workflow](../docs/toolchain-workflow.md) describes input
ownership, qualification and release creation. SDKs, media and generated work
stay private. Commands neither create GitHub repositories nor upload releases.

## Component and support scripts

prepare.py and verify-patches.py fetch and verify the pinned GCC source and
patch series. build.py, build-cxx-toolchain.py, build-runtime.py,
build-libatomic.py and build-cxx-runtime.py build the target compilers and
runtimes. build-host-tools.py and build-shared-tools.py build the Mach-O tools.
rebuild-host-inputs.py supports rebuilding the pinned host-side components.
Native 64-bit and Canadian cross builds are described in
[Linux host architectures](../docs/linux-hosts.md).

install-toolchain.py stages compiler components; bundle-host-runtime.py and
install-public-tools.py make the assembled bundle self-contained. The stage-*
scripts update a fresh candidate, while promote-toolchain.py optionally selects
an immutable local snapshot. build_inputs.py and shared_support.py are internal
shared helpers. export-patch.py exports maintained compiler changes.

nextstep-gcc, nextstep-shlib, nextstep-debug.py, prepare-sdk.py, setup-sdk.py
and target-tool-unavailable are maintained program/template sources used by
the build. Their release copies are generated in bin/ and libexec/.

Regression checks live in [tests/](../tests/README.md). Guest preparation and
console controls live in tests/guest/; fixture builders and reference/compiler
comparisons live in tests/qualification/. They are not release build steps.
