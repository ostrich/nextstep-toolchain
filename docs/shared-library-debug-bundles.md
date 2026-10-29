# Retained DWARF for fixed-VM libraries

The development `tools/nextstep-shlib` constructor accepts `--retain-debug`.
It retains each target's DWARF input objects in a sibling `.debug` directory,
rewrites the library's debug map to relative paths, and records object hashes.
Distribute the matching directory alongside the runtime for source debugging.
The runtime text/data addresses and import ABI are unchanged.

In a development checkout, `--toolchain` selects the canonical support bundle
and `--host-tools` selects an explicit cctools candidate. The historical
`mkshlib` still comes from the support bundle. Constructor, linker, assembler,
archive tools and debug-helper identities are recorded in the build record.
Installed constructors reject the development host-tools override. These
options do not promote a candidate or modify an installed snapshot.

The Intel development qualification includes source breakpoints, a private
library variable, cross-library stack unwinding and checked function returns
in an OPENSTEP guest. The existing executable debug-bundle regression also
passes relocation, malformed-input and tampered-object checks. Building without
`--retain-debug` against the same canonical tools produces an identical import
archive and runtime bytes except for the historical linker's random LC_UUID.

Four-target constructor qualification and staging/promotion remain required
before using this feature as part of the canonical distribution build chain.
