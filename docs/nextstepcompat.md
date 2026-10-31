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

## Independent use

Preserve the option to distribute and use NextStepCompat independently of this
toolchain. Its current build and header integration depend on the NeXT compiler
bundle and its SDK preparation; another compiler has not been qualified.

Header cleanup must not turn SDK adaptation into an exclusively toolchain-owned
prerequisite. Any shared SDK repairs or feature-selection policy should remain
reusable with the component. The toolchain can invoke that support automatically,
while a future standalone build can invoke it explicitly against a user-supplied
SDK. Keep compiler arithmetic, exception handling and compiler TLS support in the
compiler runtime, with their requirements documented separately.

This is a design constraint, not a commitment to support other compilers now.
Preserve the native ABI and keep compiler-specific assumptions identifiable so
future decoupling can be qualified without redesigning the library interfaces.

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
