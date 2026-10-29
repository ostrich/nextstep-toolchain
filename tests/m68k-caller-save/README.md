# m68k floating-point caller-save regression

This is a C-only reduction of a zero-sized browser viewport. Compile `layout.c`
and `check.c` separately, then link them without LTO. The message dispatcher
must remain opaque while optimizing layout. No AppKit, Foundation or browser
code is needed at runtime.

The layout keeps single-precision dimensions live across calls. On the
unfixed GCC 16.2 NEXTSTEP m68k target, caller saves store FP registers in XF
format, then some uses read the last word of that save slot as SF bits. For
720 and 440 those low mantissa words are zero. This is not a floating-point
precision difference: the stored numeric representation is being misread.

The m68k backend needs `TARGET_CAN_CHANGE_MODE_CLASS` to reject differing
modes in classes containing hardware floating-point registers. Those registers
hold numeric values after format conversion, not interchangeable memory bit
patterns. The corrected assembly restores the extended value to an FP
register and converts it when storing a single-precision result.

Build and execute the following variants in one disposable m68k guest:

- Native compiler with `-O2`: reference behavior.
- Existing cross-compiler with `-O2`: reproduce the failure.
- Existing cross-compiler with `-O2 -fno-caller-saves`: diagnostic control.
- Patched cross-compiler with plain `-O2`: qualify the actual fix.

Each successful executable must report all four rectangle checks and exit 0.
Treat failure of the old compiler as an expected negative control, not a
successful compiler qualification. Preserve compiler build records, hashes,
native halt and stopped-filesystem results. Do not use a diagnostic compiler
build as an alternative canonical toolchain; promotion remains the separate
coherent-snapshot workflow.

`prepare.py --help` lists the explicit old compiler, SDK, fixed compiler,
watchdog and output inputs. Select `--fixed-toolchain` to qualify a complete
staged bundle, or `--candidate` for an uninstalled compiler build. Keep the old
immutable snapshot as `--toolchain` after promotion so the negative control
continues to reproduce the original failure. It builds all three cross variants
and stages the same two C files for native guest compilation. Transfer the generated payload to a disposable NEXTSTEP m68k system and run
its run.sh with a bounded watchdog. `run.sh` requires the old compiler's four recorded checks
and exit 1, and successful four-rectangle results
from the native, disabled-optimization and patched variants.
