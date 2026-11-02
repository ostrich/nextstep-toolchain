# Intel aggregate returns and stack probes

GCC patch 0014 corrects the scratch-register selection used by looped stack
probes on NeXT/i386. This ABI passes an aggregate-result pointer in EBX. A
callee-save push preserves EBX for the caller, but the incoming pointer must
also remain intact until the function body consumes it. The old selector
mistook that saved register for available scratch when the ordinary argument
registers were occupied.

The patch excludes the target hook's dedicated aggregate-result register from
unsaved scratch candidates. The existing push/pop fallback remains available.
It does not disable optimization or stack-clash protection.

## Regression

`tests/i386-stack-probe-sret.c` returns a 1,460-byte aggregate from a function
with a volatile 64 KiB frame and three integer arguments. Three rounds check
every result byte. A separate scalar-return function checks argument
preservation with the same frame size.

Build it through the public driver at both optimization levels:

```sh
bin/nextstep-gcc --sdk SDK -arch i386 -O1 -fstack-clash-protection \
    tests/i386-stack-probe-sret.c -o stack-probe-test
```

Repeat with `-O2`, then execute both binaries in a disposable Intel guest.
The previous compiler fails all three aggregate-return rounds at both levels;
the corrected compiler passes the aggregate and scalar checks. Both were run
in the same NEXTSTEP 3.3 guest, which halted cleanly and passed filesystem
checks. An independent reduced Rust theme parser also returned the correct
nested values after recompiling its generated C with the corrected backend.

The complete four-target compiler was rebuilt from the hash-locked GCC release
and all maintained patches. All 66 basic-runtime object files per target match
the previously qualified objects byte for byte. The large-frame control's
optimized assembly is unchanged on m68k, HPPA and SPARC. All 16 NIHS C/C++
header-order checks pass. This is Intel native qualification of the correction,
not a repeated full regression campaign on the other three architectures.

The subsequent [NIHS prologue qualification](stack-prologues-validation.md)
covers the corresponding hidden-argument and large-frame paths on all four
architectures.
