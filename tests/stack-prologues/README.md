# Hidden arguments and large-frame prologues

This focused compiler regression checks aggregate-result pointers, ordinary
arguments and nested-function static chains across large stack frames. It is
intended to detect register clobbering like the NeXT/i386 stack-probe defect;
it is not a general stack-overflow or guard-page test.

The source defines 18 combinations: results of 12, 1,460 and 8,196 bytes, with
volatile frames of 64, 3,584, 4,096, 4,608, 12,288 and 65,536 bytes. Each runs
three input rounds through direct-only functions, address-taken functions,
direct nested calls and nested-function pointers. Separate scalar functions
check ordinary argument preservation. Every result byte is verified, along
with page-spaced volatile frame contents. Each executable reports 234 result
and scalar checks; frame-content checks are additional.

Direct-only functions are intentionally separate from address-taken functions.
Otherwise taking the address can prevent the local register-argument convention
that exposed the original Intel failure. Nested-function pointers exercise
GCC's actual trampoline path and captured volatile state.

## Build and run

Use the canonical compiler and an immutable pre-fix bundle for the negative
control. All work stays in a fresh output directory:

```sh
python3 tests/stack-prologues/build.py --sdk SDK \
    --baseline OLD-TOOLCHAIN --output work/stack-prologues
```

This builds optimized thin executables and assembly for NIHS at `-O1`, `-O2`
and `-O3`, with `-fstack-clash-protection`, then creates a flat fat-binary
payload. The build record includes compiler manifests, source and output hashes,
commands and diagnostics. Execute `payload/run.sh` in disposable guests using
the project's existing native test harness. Intel additionally runs the
original reproducer built with the old compiler: it must return exactly 1.
A crash or unexpected success does not satisfy the negative control.

Inspect the generated assembly as well as the runtime results. The flag alone
does not establish that a backend emits probes. In the tested configuration,
Intel and SPARC generate looped probes, while m68k and HPPA generate ordinary
static large-frame allocation. Successful m68k/HPPA execution therefore checks
large-frame argument preservation, not static stack-clash protection.

See [qualification](../../docs/stack-prologues-validation.md) for recorded
results and the ABI/prologue audit.
