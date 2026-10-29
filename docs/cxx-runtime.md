# C++ runtime

The toolchain supplies a static GCC C++ runtime for NEXTSTEP 3.3 Intel, NeXT
68k, HPPA and SPARC. Programs use the original system libraries together with
libstdc++, libsupc++, libgcc, libatomic and NextStepCompat. Use nextstep-g++
for both compilation and final linking.

## Supported facilities

The runtime includes SJLJ exceptions, RTTI, allocation, static initialization,
containers, streams, filesystem adapters, C-locale numeric conversions,
cthreads-based std::thread, thread-local destructors and atomic operations.
Target startup establishes the floating-point precision needed by modern
compiled code. It does not replace the system libc or native Objective-C
runtime.

General C/POSIX adapters belong to [NextStepCompat](../nextstepcompat/README.md).
The C++ threading bridge is a separate GCC gthread implementation; see
[runtime/threads](../runtime/threads/README.md) for lifecycle, TLS and deadline
semantics, and [atomic operations](../runtime/threads/atomics.md) for CPU and
progress requirements.

## Limits

The modern C++ ABI is not the original NeXT C++ ABI. Do not exchange C++
objects or exceptions with code built by the original compiler. C interfaces
are the appropriate boundary to original system libraries.

Shared C++ runtimes, PIC and LTO are not supported by this runtime build.
The locale model is C/POSIX, rather than modern Unicode locales. Lock-based
atomics are neither process-shared nor safe for signal handlers. HPPA's
byte-sized atomic_flag has a documented lock-free progress limitation.
Native operating-system limits still apply to filesystem and thread APIs.

## Qualification

Native NEXTSTEP 3.3 tests on all four targets cover ABI interoperability,
exceptions, threads, TLS destruction, atomics, numeric conversion, file I/O
and separately compiled objects. Intel execution is also checked on OPENSTEP
4.2. Pinned application-sized compiler regression fixtures exercise parsing,
code generation and binary serialization. These are toolchain tests, not
qualification of separately distributed application ports or exhaustive ISO
C++ conformance.

See [release validation](validation.md) for the distributed bundle's checks
and [building](cxx-toolchain.md) for the rebuild and test entry points.
