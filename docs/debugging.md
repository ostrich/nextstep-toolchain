# Classic Mach-O source debugging

The maintained GCC patch enables DWARF for all four NEXTSTEP targets, with
DWARF 4 as the default for -g. Debug output is selected with -g; ordinary builds need not retain debug objects.

The assembler emits debug sections, but the classic linker leaves source
information in the original objects. With -g, the compiler wrapper now retains
referenced objects and archives in PROGRAM.debug/ARCH, names them by SHA-256,
and rewrites object-map paths relative to PROGRAM. Keep that directory beside
the executable. Sources may reside elsewhere and use GDB source-path mapping.
Each retained-object manifest identifies its architecture, thin executable,
final container and retained bytes. Archive member timestamps remain distinct
from the archive file's own timestamp.

Use the modern GDB port's Mach-O reader patches. They resolve retained bundles,
apply plain-address debug relocations on the classic big-endian targets and
select universal executable/object/archive slices for the chosen architecture.
The system's original debugger remains useful for historical STABS programs;
current upstream GDB removed STABS source-debugging support.

The wrapper passes -no_uuid because the original loader rejects LC_UUID.
Debug-map rewriting preserves mapped file extents and fails explicitly on
unsupported layouts or growth beyond the reserved link-edit mapping. -g0 does
not create a retained-object directory. Relocatable outputs keep their DWARF.

## Regression gates

- tests/test-dwarf-i386-registers.py checks the actual Mach-O CIE uses
  standard DWARF ESP register 4, rather than the historical stabs map.
  The corresponding i386-only patch preserves stabs numbering outside DWARF.
- tests/test-dwarf.py checks optimized assembly, object and linked source/type
  reading on one or all targets.
- tests/test-dwarf-multiunit.py checks distinct compilation units and an archive
  after deleting original inputs and moving the retained bundle.
- tests/test-dwarf-universal.py checks fat executables, fat objects and fat
  archives on NIHS, including differing archive/member timestamps.
- tests/test-debug-bundle.py checks relocation, malformed-input failure without
  replacing the executable, and content-addressed object integrity.
- tests/test-dwarf-readers.py runs the linker CU reader under ASan/UBSan against
  valid, truncated and mutated inputs.

Use a debugger with classic NeXT Mach-O and the retained-object conventions
above. A debugger is not included in this toolchain download. Test source
lookup and target execution with the debugger version you intend to use.
