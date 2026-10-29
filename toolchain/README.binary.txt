GCC 16.2.0 for NEXTSTEP 3.3
=========================

This Linux-hosted compiler builds Intel, NeXT 68k, SPARC and HPPA programs.
It includes C, C++, Objective-C and Objective-C++ frontends, classic Mach-O
tools and the modern static C++ runtime. It does not run on NEXTSTEP itself.

Host requirements
-----------------

This low-level staging template requires x86-64 Linux, Python 3.11+, glibc
with 32-bit library support, ISL, MPC, MPFR, GMP and Zstandard. The portable
release bundles those host libraries; follow its root README instead. The classic Mach-O tools are 32-bit Linux executables.
The compiler frontends are 64-bit Linux executables. Host libraries must
provide the versions required by these binaries.

Provide your own private NEXTSTEP 3.3 SDK, containing lib/ and usr/include/.
No original SDK, system library or VM image is included in this bundle.

Usage
-----

Set the SDK location, then compile from this directory:

    export NEXTSTEP_SDK=/path/to/your/sdk33
    bin/nextstep-g++ -arch i386 -O2 -std=gnu++17 hello.cc -o hello

For a fat executable, repeat -arch:

    bin/nextstep-g++ -arch i386 -arch m68k -arch sparc -arch hppa \
      -O2 -std=gnu++17 hello.cc -o hello-fat

Use bin/nextstep-gcc for C. Use bin/nextstep-g++ or nextstep-gcc --cxx when
linking separately compiled C++ objects. Headers, startup and runtime libraries
are selected automatically for each architecture. The bundle can be moved;
its tools and libraries are located relative to the driver. The SDK remains
external. toolchain.json contains installed-file hashes and relative paths.

NextStepCompat
--------------

NextStepCompat supplies general libc adapters, including bounded formatting,
numeric conversion and path handling. Its headers and static library are
selected automatically for C and C++ programs. No separate guest package is
required. Public headers are under include/nextstepcompat/ and each target's
libnextstepcompat.a is under lib/ARCH/. Where needed, standard C names map to
ns33_ adapters so corrected implementations can coexist with native symbols.
toolchain.json records the component version and archive locations.
Single-byte character conversion, classification and width APIs preserve the
16-bit wchar_t ABI. MB_CUR_MAX is one; UTF-8 locales and wide stream I/O are
not provided.
The library also supplies mkfifo and core POSIX signal operations over native
BSD interfaces. SA_RESTART and SA_ONSTACK are supported. SA_NOCLDSTOP and
unknown action flags return EINVAL. Masks remain process-wide; this does not
provide pthread signal handling or full modern POSIX signal conformance.

Runtime scope
-------------

The runtime provides SJLJ exceptions, RTTI, allocation, static initialization,
containers, streams, filesystem operations, cthreads-based std::thread and
atomic operations. It uses the C/POSIX locale. Shared C++ libraries, PIC, LTO,
original NeXT C++ binary ABI compatibility are not provided. NextStepCompat
provides a separately documented pthread compatibility API with explicit limits. Not every modern standard-library facility is available through
the original operating system's C interfaces.

Intel atomic helpers require an i486 or newer CPU. SPARC v8 general atomics
use locks; HPPA synchronization helpers also use locks. HPPA's byte-sized
atomic_flag provides mutual exclusion but not the standard's unconditional
lock-free progress guarantee. Lock-based atomics are not process-shared or
safe for signal-handler use.

Four-target runtime regressions and substantial application tests have run
in actual NEXTSTEP 3.3 guests, with Intel checks on OPENSTEP 4.2. These focused
tests do not establish full C++ standard-library conformance.

Licenses are under share/licenses/.
