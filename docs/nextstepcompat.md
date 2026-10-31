# NextStepCompat integration

[NextStepCompat](../nextstepcompat/README.md) is the toolchain's reusable C and
POSIX compatibility layer. The public driver automatically selects its headers
and static library for each target. Programs built this way need no separate
NextStepCompat installation on the guest.

The original SDK remains external. Compatibility headers repair declarations,
preserve native data layouts and map corrected functions to ns33_ symbols when
necessary. Original system symbols remain available to existing binaries.
This is not a replacement libc, a Unicode locale implementation or a promise
of complete POSIX conformance.

## Ownership and updates

Sources, headers, upstream pins, adaptation patches and tests live under
nextstepcompat/. Compiler arithmetic, exceptions, GCC TLS and the C++ gthread
bridge belong to runtime/ and the GCC patches instead.

Use nextstepcompat/build.py for static libraries and
nextstepcompat/build-shared.py for an explicitly selected shared runtime.
The component README describes their arguments and output layout. Install
changes only into a fresh stage, then test and regenerate the integrity
manifest. Never change a qualified bundle in place. Follow the
[toolchain workflow](toolchain-workflow.md).

## SDK preparation and future native builds

NextStepCompat owns application APIs, corrected library behavior, public
compatibility declarations and symbol redirects. The toolchain's
`tools/prepare-sdk.py` owns syntax repairs needed to compile original SDK
headers with modern GCC. It generates private copies; it does not modify or
distribute the original SDK.

Keep the option of porting NextStepCompat to the original NeXT compiler.
That configuration would use the original SDK with the component's API headers
and must not require modern-compiler SDK preparation. The full component still
contains compiler-specific constructs and has not been qualified with the
native compiler. This cleanup does not claim to complete that port.

Two small component-owned headers keep common behavior in one place:
`ns33-feature-profile.h` selects the user-space POSIX profile, and
`ns33-fdset.h` corrects FD_ZERO using standard C memset. Neither requires the
SDK preparer or modern GCC builtins. The preparer copies these headers into its
private overlay so qualified SDK includes use the same implementation.
Compiler-macro normalization and modern signal-handler syntax remain in SDK
preparation. Runtime API additions remain in NextStepCompat. The shared
profile leaves KERNEL builds unchanged, but the complete compatibility layer
is intended for user-space applications and is not qualified kernel support.

The current modern-toolchain build and update helpers check that the installed
SDK preparer supports these headers before creating output or changing the
bundle. Update those paired components together in a fresh stage. Native
compiler support remains a future qualification task. Compiler arithmetic,
exception handling and compiler TLS support remain separate runtime concerns.

## Contracts and coverage

The component's [API overview](../nextstepcompat/README.md#scope),
[coverage audit](../nextstepcompat/docs/api-coverage.md),
[pthread matrix](../nextstepcompat/docs/pthread-coverage.md) and
[test guide](../nextstepcompat/tests/README.md) describe implemented behavior,
known native limitations and reproducible checks. Component test results do
not imply that an arbitrary application using those interfaces is qualified.

Shared builds use the explicit function slots and address reservations in
nextstepcompat/shared.json. Static and shared libraries are different link
inputs; preserve existing occupied entries when updating the shared ABI.
See [shared-library construction](shared-libraries.md).
