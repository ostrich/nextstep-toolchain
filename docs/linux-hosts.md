# Linux host architectures

The host architecture is independent of the NEXTSTEP target. A native Linux
arm64 or x86-64 compiler can produce Intel, m68k, HPPA and SPARC Mach-O files.
The maintained classic-tool patches separate host pointers from the target's
32-bit symbol records, relocation words, archive fields and thread commands.
Both host architectures use the same patches.

## Native builds

Use the normal source-build entry point on the chosen Linux host. The classic
Mach-O tools and fixed-VM shared-library constructor now default to the native
host ABI. Their `--host-abi i386` option retains the older 32-bit x86 build for
regression comparisons; it is not needed for a native 64-bit bundle.

`tests/test-host-abi.py` compares assembler objects and selective archive links
against a reference tool build. Archive, BSS, strip, ordered-link and shared
library tests cover the surrounding file-format operations. These are host
tests; target execution remains a separate qualification step.

## Building arm64 executables on x86-64

An optional Canadian cross build uses an arm64 Linux C/C++ cross compiler and
arm64 development libraries for GMP, MPFR, MPC, ISL, Zstandard and zlib. Build
in a clean environment rather than mixing another architecture's configure
results into an existing build directory.

For each NEXTSTEP target, the low-level compiler builder accepts:

```
python3 tools/build.py --arch i386 --languages c,c++,objc,obj-c++ \
  --thread-model nextstep --exception-model sjlj \
  --host aarch64-linux-gnu \
  --build-target-compiler /path/to/qualified-bundle/libexec/gcc/i386/xgcc \
  --output work/arm64-compilers/i386
```

The build-target compiler runs on the build machine and targets the same
NEXTSTEP architecture. GCC uses it for build-time target queries. It is not
shipped in the arm64 bundle. Repeat for m68k, HPPA and SPARC.

The classic tools accept `--cc` pointing to a compiler or wrapper that selects
the arm64 Linux execution target. For Clang, that wrapper can contain:

```
#!/bin/sh
exec clang --target=aarch64-linux-gnu "$@"
```

Make the wrapper executable, then build both components against the same host
ABI and support library:

```
python3 tools/build-host-tools.py --cc /path/to/arm64-clang \
  --output work/host-tools-arm64
python3 tools/build-shared-tools.py --cc /path/to/arm64-clang \
  --host-build work/host-tools-arm64 --output work/shared-tools-arm64
```

The cross compiler must have access to arm64 Linux development headers and
libraries, including UUID headers. An x86-only development installation is
insufficient.

`tools/assemble-release.py` can reuse a qualified portable bundle's target
headers and runtime archives while replacing its host programs. Rehosting
requires explicit `--shared-tools` and `--nextufs` inputs as well as the
compiler builds and classic tools. Run assembly on the destination host so
stripping, dependency collection and private-loader checks use that host.

The resulting bundle must execute on arm64 Linux before release. Merely
cross-compiling or inspecting ELF headers does not establish usability.
