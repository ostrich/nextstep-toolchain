# NEXTSTEP toolchain

Build NEXTSTEP 3.3 applications on Linux for Intel, NeXT 68k, HPPA and SPARC.
GCC 16.2.0 supports C, C++, Objective-C and Objective-C++, with classic Mach-O
tools and native Installer package creation. Intel binaries also run on
OPENSTEP 4.2; m68k and SPARC OPENSTEP compatibility is expected but untested.

Extract the binary download anywhere. Python 3.11+ is required. No root access,
system toolchain installation or system multilib setup is needed. Native
64-bit builds support Linux x86-64 and arm64.
The usage below describes the binary archive. This source checkout contains
the build scripts; see the local source-build instructions below.

## Set up the private SDK

Supply your own NEXTSTEP 3.3 developer CD image:

```sh
bin/setup-sdk developer.iso
```

Setup reads the images with bundled nextufs, without mounting or modifying
media. It creates sdk/nextstep3.3 and refuses to overwrite an existing SDK.
SDK files are private inputs and are not included in our downloads.

## Compile and package

Run these commands from the extracted bundle's root directory after SDK setup.
This example builds the supplied Hello program for all four architectures and
stages it for installation as `/usr/local/bin/hello` in the guest. Use a fresh
`hello-stage/` directory and manifest for the example.

```sh
umask 022
mkdir -p hello-stage/usr/local/bin
bin/nextstep-gcc -arch m68k -arch i386 -arch hppa -arch sparc -O2 \
    examples/hello/hello.c -o hello-stage/usr/local/bin/hello
chmod 755 hello-stage/usr/local/bin/hello
bin/nextpkg init hello-package.json --name Hello --version 1.0 --root hello-stage
```

Edit `hello-package.json` to set the package title and description, then build
and validate it:

```sh
bin/nextpkg build hello-package.json --output dist
bin/nextpkg check dist/Hello-1.0-1.pkg.NIHS.tar.gz
```

The archive contains `Hello.pkg`; its version is `1.0-1`. `NIHS` identifies
NeXT 68k, Intel, HPPA and SPARC. Use `-arch i386` alone for an Intel build;
that package's suffix will be `.pkg.I.tar.gz`. Package creation needs neither
root access nor a guest VM. Extraction and guest installation are described
in the [packaging guide](docs/user-packaging.md).

Use nextstep-g++ for C++. SDK selection is --sdk, then NEXTSTEP_SDK, then the
bundle's sdk/nextstep3.3 directory. Add the absolute bin directory to PATH if
preferred. Ordinary Make and Autoconf builds remain ordinary builds: set CC,
CXX and the appropriate cross-compilation host triplet for your target.
Do not execute configure test programs on Linux and mistake them for target tests.

workspace/ is an optional location for projects. Source trees can live anywhere.
Keep pristine sources, patches, build directories and staging files separate.
Updates should be extracted alongside the old toolchain; never overwrite your
SDK or project workspace. Runtime testing on the target remains necessary.

## Source and local builds

This repository owns compiler and cctools patches, runtime adaptations,
NextStepCompat, nextpkg and the pinned nextufs sources. Source pins and build
recipes are retained alongside their components. tools/assemble-release.py
creates a new release stage from a qualified compiler bundle. It does not
rebuild the compiler. See docs/toolchain-workflow.md for compiler rebuilding.
Builds and release uploads are local; there is no GitHub Actions workflow.

## Build from source locally

Building from source requires a C/C++ host compiler, Clang, Make, Git, patch,
Bison, Flex, Texinfo, Python 3.11+, binutils and development libraries for GMP,
MPFR, MPC, ISL, Zstandard, zlib and UUID. Use a source checkout without
spaces; the resulting download supports relocation into paths with spaces.

Bootstrap a private SDK before the first compiler is available:

```sh
make -C src/nextufs WITH_FUSE=0
python3 tools/setup-sdk.py developer.iso --nextufs src/nextufs/nextufs \
    --output work/sdk --skip-link-checks
python3 tools/build-local-release.py --sdk work/sdk --output work/release
```

The bootstrap switch skips SDK link checks only until a compiler exists.
Ordinary binary-download setup always checks all four targets. The source
build records its inputs, builds optimized compilers and runtimes, and stages
tools into a new output directory. It installs nothing and uploads nothing.
Shared-library construction details are in docs/shared-libraries.md.
See [build and release tools](tools/README.md) and [tests](tests/README.md)
for maintainer entry points and qualification helpers.

Release checks and their limits are described in [validation](docs/validation.md).
Local archives are created with tools/create-release.py after testing a fresh
stage. No remote repository or upload is part of that command.

See the [documentation index](docs/README.md) for runtime, ABI, debugging and
shared-library references.
