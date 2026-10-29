# Building and testing the C++ toolchain

Use the [source-build instructions](../README.md#build-from-source-locally)
for the complete distributable bundle. tools/build-local-release.py builds
optimized compilers and target runtimes and stages a relocatable release.
Its --jobs limit applies to each of four simultaneous targets, so choose it
with host memory and CPU capacity in mind. Do not run concurrent builds in
the same output directories.

## Components and provenance

toolchain/cxx-build-set.json describes each target's compiler, basic runtime,
C++ runtime and atomic runtime outputs. The build scripts replay maintained
patches against pinned upstream sources and record commands and input/output
hashes. Staging verifies that compiler and runtime inputs agree. SDK files,
build-tree symlinks and configure-only support archives are not shipped.
Host binaries are stripped; target archives retain symbols needed for linking.

The low-level tools/build-cxx-toolchain.py builds the four targets. Use the
complete release entry point unless deliberately updating one component.
The [workflow](toolchain-workflow.md) explains fresh staging and optional
local snapshot promotion. Build completion alone does not establish execution.

## Compile and link

```sh
nextstep-g++ -arch i386 -O2 -std=gnu++17 hello.cc -o hello
nextstep-g++ -arch i386 -arch m68k -arch sparc -arch hppa \
  -O2 -std=gnu++17 hello.cc -o hello-fat
```

The public driver chooses matching headers, startup and libraries. Use
nextstep-g++ or nextstep-gcc --cxx to link C++ objects when no source filename
identifies the language. Repeated -arch options support fat objects and final
executables. The usual -nostdlib, -nodefaultlibs, -nostartfiles and -nostdinc++
controls suppress the corresponding automatic inputs.

See [runtime capabilities](cxx-runtime.md), [SDK integration](nextstepcompat.md)
and [source debugging](debugging.md) for supported behavior and limitations.

## Tests

Run tests/test-installed-cxx.py --help for installed-bundle checks. Supply
--prefix, --sdk and a fresh --output directory. It checks hashes and symlinks,
builds runtime and ABI fixtures, extracts target slices and tests relocation.
The relocation check temporarily moves the bundle: do not build other programs
from it at the same time.

The compiler regression sources live under tests/, including C++, threading,
DWARF, driver-output, header-order and architecture-specific cases. Native
execution requires separately prepared target systems; this repository does
not distribute guest images or depend on a particular lab VM name.

Run tools/verify-patches.py --full to check exact patch replay and unchanged
upstream files. [Release validation](validation.md) distinguishes build,
inspection and actual target execution.
