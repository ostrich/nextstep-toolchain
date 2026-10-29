# NEXTSTEP toolchain

GCC @GCC_VERSION@ cross-compiles C, C++, Objective-C and Objective-C++ programs
for NEXTSTEP 3.3 on Intel, NeXT 68k, HPPA and SPARC. Binaries can also
run on OPENSTEP, subject to the APIs used. Intel is tested; SPARC and m68k
are expected to work but have not been tested.

This is a Linux x86-64 toolchain. Extract it anywhere; it installs nothing.
It needs Python 3.11+ and a Linux kernel with 32-bit x86 execution support.
The other host runtime libraries are included, so system multilib packages
and separate GMP, MPFR, MPC, ISL or Zstandard installations are not needed.

## Set up your SDK

Provide your own NEXTSTEP 3.3 developer CD image:

```sh
bin/setup-sdk /path/to/developer.iso
```

Setup reads the image without mounting or modifying it, extracts the private
SDK under sdk/nextstep3.3, and checks compilation and linking for all four
targets. It refuses to overwrite an existing SDK. No SDK or CD image is
included in this download.

## Build programs

```sh
bin/nextstep-gcc -arch i386 -O2 hello.c -o hello
bin/nextstep-gcc -arch m68k -arch i386 -arch hppa -arch sparc \
    -O2 hello.c -o hello-fat
```

Use nextstep-g++ for C++. Add this bundle's absolute bin directory to PATH
for normal Make/configure workflows. Conventional target-prefixed commands
are included, such as i386-next-nextstep3.3-gcc, g++, ar and ranlib.

```sh
export PATH="/path/to/nextstep-toolchain/bin:$PATH"
./configure --host=i386-next-nextstep3.3 --prefix=/usr/local
make
make DESTDIR="$PWD/stage" install
```

Application-specific porting changes and target-side tests are usually needed.
Configure cannot run NEXTSTEP test programs on Linux. See PORTING.md.
SDK selection is explicit --sdk, then NEXTSTEP_SDK, then sdk/nextstep3.3.
NextStepCompat is included in the compiler's static runtime support; ordinary
programs do not require a separate NextStepCompat guest package.

## Make Installer packages

From the bundle's root directory after SDK setup, this complete example
builds the supplied Hello program for all four architectures and stages it
for installation as `/usr/local/bin/hello` in the guest. Use a fresh
`hello-stage/` directory and manifest:

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

The `.NIHS` suffix matches this four-architecture executable. An Intel-only
payload produces `.I` instead. The archive contains `Hello.pkg`, and Installer
shows version `1.0-1`. Package creation needs no root access or guest VM.

Extract the outer `.tar.gz`, transfer `Hello.pkg` to the guest, and open it in
the native Installer as root. Leave the package's internal files intact.
See [the packaging guide](docs/packaging.md) for extraction, manifests,
permissions and hooks. `examples/hello` also supplies a Makefile and manifest.
For shared-library construction, see [shared libraries](docs/shared-libraries.md).

workspace/ is optional. Projects may live anywhere. Extract updates beside the
old bundle and reuse your private SDK with --sdk or NEXTSTEP_SDK. Do not
replace or delete your workspace as part of a toolchain update.

Licenses and component notices are under share/licenses. toolchain.json and
share/host-runtime.json identify the files and runtime inputs in this bundle.

See docs/validation.md for the release checks and their scope.
