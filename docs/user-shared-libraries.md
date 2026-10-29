# Shared libraries

NEXTSTEP uses fixed-address .shlib libraries rather than ELF shared objects.
The bundle includes nextstep-shlib and its underlying construction tools.
No original guest tools are required for construction.

A library needs a reviewed specification defining its guest install name,
exported symbols and reserved text/data addresses. Addresses must not collide
with system or other installed libraries. Do not choose an address from an
example without checking existing allocations. Keep existing function slots
and public data layouts stable when updating a library.

Compile objects with the specification, then construct the runtime and import
archive. For example, after preparing a valid shared.json:

```sh
nextstep-gcc --shared-exports shared.json -O2 -arch i386 -c example.c -o example.o
nextstep-shlib --spec shared.json --output libexample.1.shlib \
  --import-library libexample.a --build-record shared-build.json example.o
nextstep-gcc -arch i386 main.c -L. -lexample -o example
```

The .shlib goes into the guest runtime package. The .a is a link-time import
archive for developers, not a static implementation of the library. Test the
library and unchanged consumers on every architecture claimed by the package.
The source repository's docs/shared-libraries.md documents the specification
and constructor details. This is an advanced operation; ordinary application
ports can start with the supplied runtime and static application libraries.
