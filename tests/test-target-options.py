#!/usr/bin/env python3
"""Check the target identity and fail-closed assembly-only tool configuration."""
import argparse
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
args = p.parse_args()
build = ROOT / 'work' / ('build-' + args.arch) / 'gcc'
out = ROOT / 'work' / ('target-options' if args.arch == 'i386' else 'target-options-' + args.arch)
out.mkdir(parents=True, exist_ok=True)
source = out / 'identity.c'
source_text = '''#if !defined(NeXT) || !defined(__MACH__) || !defined(CPU_MARKER)
#error wrong target identity
#endif
_Static_assert(__SIZEOF_POINTER__ == 4, "pointer width");
_Static_assert(__SIZEOF_LONG__ == 4, "long width");
_Static_assert(__builtin_types_compatible_p(__SIZE_TYPE__, unsigned long), "size type");
_Static_assert(__builtin_types_compatible_p(__PTRDIFF_TYPE__, long), "ptrdiff type");
_Static_assert(__builtin_types_compatible_p(__WCHAR_TYPE__, unsigned short), "3.3 wchar type");
_Static_assert(sizeof(L"x"[0]) == 2, "3.3 wide literal width");
_Static_assert(sizeof(long double) == 12, "3.3 extended float storage");
struct double_alignment { char c; double d; };
_Static_assert(sizeof(struct double_alignment) == MEMBER_SIZE, "3.3 member alignment");
int identity(int x) { return x + 1; }
'''
sizes = {'i386': (12, 12), 'm68k': (12, 10), 'sparc': (8, 16), 'hppa': (8, 16)}
source_text = source_text.replace('__PTRDIFF_TYPE__, long', '__PTRDIFF_TYPE__, ' + ('long' if args.arch in ('i386', 'm68k') else 'int'))
source_text = source_text.replace('sizeof(long double) == 12', 'sizeof(long double) == ' + str(sizes[args.arch][0]))
marker = {'i386': '__i386__', 'm68k': '__m68k__', 'sparc': '__sparc__', 'hppa': '__hppa__'}[args.arch]
source.write_text(source_text.replace('CPU_MARKER', marker).replace('MEMBER_SIZE', str(sizes[args.arch][1])))
compiler = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2']
records = []
for name, flags, expected, marker in [
    ('identity', ['-std=c11', '-S'], True, None),
    ('reject-pic', ['-fPIC', '-S'], False, 'requires non-PIC' if args.arch == 'hppa' else 'position-independent code is not implemented'),
    ('reject-host-assembler', ['-c'], False, 'supports assembly output only')]:
    command = compiler + flags + [str(source), '-o', str(out / (name + '.out'))]
    r = subprocess.run(command, capture_output=True, text=True)
    passed = (r.returncode == 0) == expected and (marker is None or marker in r.stderr)
    records.append({'name': name, 'passed': passed, 'exitcode': r.returncode,
                    'stdout': r.stdout, 'stderr': r.stderr})
    print(name + ': ' + ('PASS' if passed else 'FAIL'), flush=True)
(out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
if not all(r['passed'] for r in records):
    raise SystemExit(1)
