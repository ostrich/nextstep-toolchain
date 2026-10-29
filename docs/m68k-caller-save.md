# m68k floating-point caller-save corruption

GCC 16.2's m68k backend allowed incompatible floating-point representations
to be treated as low-part bitcasts. A browser exposed the problem by keeping
window dimensions live across Objective-C calls: its initial window was
720x480, but later toolbar and document rectangles acquired zero widths.
The document view was initialized at 0x0, rendering nothing and stalling a
subsequent resize. This reproduced independently of the browser in C.

## Cause and fix

A hardware FP register holds a numeric value in its internal representation.
Saving that register in XF format writes a 12-byte extended floating-point
representation. Reading the last four bytes is not a conversion to SF format.
For the dimensions in the regression, that word is zero. The old generated
code performed precisely that substitution after a caller save.

Patch 0010 supplies `TARGET_CAN_CHANGE_MODE_CLASS` for m68k. It rejects changes
between differing modes for register classes intersecting the hardware FP
registers, while preserving same-mode operations and non-FP register behavior.
The fixed assembly restores the saved extended value to an FP register and
converts it when storing a single-precision result. Caller saves and normal
`-O2` remain enabled. No application-source workaround or ABI change is needed.

This is the same kind of restriction described by GCC's target-hook contract
and implemented for x87 registers in `ix86_can_change_mode_class`. The relevant
sources are `gcc/target.def`, `gcc/config/m68k/m68k.cc` and
`gcc/config/i386/i386.cc`. See the official
[GCC register-class documentation](https://gcc.gnu.org/onlinedocs/gccint/Register-Classes.html).

## Execution evidence

`tests/m68k-caller-save` contains the two-translation-unit C reduction, payload
builder, bounded guest script and machine-readable results. Opaque message
calls preserve the register-allocation situation without requiring AppKit or
Foundation. All variants ran in one disposable NEXTSTEP 3.3 m68k guest:

| Compiler/configuration | Result |
| --- | --- |
| Native GCC 2.5.8, `-O2` | All four rectangle checks pass |
| Unfixed GCC 16.2, `-O2` | Initial window passes; toolbar, URL and scroll rectangles fail |
| Unfixed GCC 16.2, `-O2 -fno-caller-saves` | All four checks pass |
| Patched GCC 16.2, normal `-O2` | All four checks pass |

The native C regression isolates the compiler failure without depending on a
browser or GUI port. The maintained patch series includes the fix; see
[release validation](validation.md) for current bundle qualification.
