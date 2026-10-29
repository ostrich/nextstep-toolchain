# GCC target patches

Apply patches in series order to the exact GCC release in ../sources.lock.json.
Use tools/prepare.py --patched and tools/verify-patches.py --full from the
repository root. Generated source edits are not a substitute for this series.

| Patch | Purpose |
| --- | --- |
| 0001 | Intel classic NeXT target, calling convention, assembler output and safe code padding. |
| 0002 | Historical SDK preprocessing, C/C++ linkage and original Objective-C runtime metadata. |
| 0003 | Shared NeXT definitions and m68k calling, layout and absolute switch-table conventions. |
| 0004 | SPARC and HPPA Mach-O targets, aggregate calls and Objective-C argument encodings. |
| 0005 | C++ runtime configuration, static weak coalescing, native types and C-locale support. |
| 0006 | Exact HPPA ldil integer constants without inappropriate relocation rounding. |
| 0007 | Consistent m68k local stack alignment, preventing overlap with saved return state. |
| 0008 | DWARF generation on the four NeXT targets. |
| 0009 | Intel DWARF register numbering while preserving historical STABS numbering. |
| 0010 | Correct m68k floating-register mode conversions across caller saves. |
| 0011 | HPPA complex calls and trampolines, Intel dynamic stack alignment and driver intermediate-output handling. |
| 0012 | m68k copysign sign transfers through integer operations. |
| 0013 | m68k single-precision multiplication rounded once at its destination. |

Target hooks are constrained to the restored NeXT configurations where
applicable. The series does not establish support for every upstream GCC
feature. See [target ABI evidence](../docs/architecture-evidence.md),
[runtime scope](../docs/cxx-runtime.md), [debugging](../docs/debugging.md) and
[release validation](../docs/validation.md).
