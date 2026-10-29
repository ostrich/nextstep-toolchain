#!/usr/bin/env python3
"""Exercise separate option arguments and persistent GCC auxiliary outputs."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
tc, sdk, out = (x.resolve() for x in [a.toolchain, a.sdk, a.output])
out.mkdir(parents=True, exist_ok=False)
record = []
for arches in [['i386'], ['m68k'], ['hppa'], ['sparc'], ['i386', 'm68k', 'hppa', 'sparc']]:
    for variant in ['default', 'cwd', 'obj', 'explicit', 'link']:
        d = out / ('-'.join(arches) + '-' + variant)
        d.mkdir()
        (d / 'obj').mkdir()
        (d / 'dumps').mkdir()
        (d / 'probe.c').write_text('int main(void){return 0;}\n')
        cmd = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk)]
        for arch in arches:
            cmd += ['-arch', arch]
        cmd += ['--param', 'max-inline-insns-single=20', '-O2', '-fdump-tree-optimized']
        if variant == 'explicit':
            cmd += ['-save-temps', '-dumpdir', 'dumps/', '-dumpbase', 'named.c', '-dumpbase-ext', '.c']
        else:
            cmd += ['-save-temps' + ('=' + variant if variant in ['cwd', 'obj'] else '')]
        cmd += ['probe.c', '-o', 'obj/app' if variant == 'link' else 'obj/result.o']
        if variant != 'link':
            cmd += ['-c']
        result = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        row = {'arches': arches, 'variant': variant, 'command': cmd,
               'exitcode': result.returncode, 'stderr': result.stderr}
        record.append(row)
        (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise SystemExit(result.stderr)
        base = 'named' if variant == 'explicit' else ('app-probe' if variant == 'link' else 'result')
        directory = d / ('dumps' if variant == 'explicit' else ('.' if variant == 'cwd' else 'obj'))
        for arch in arches:
            name = base + ('-' + arch if len(arches) > 1 else '')
            assert (directory / (name + '.s')).is_file(), (directory, name)
            assert (directory / (name + '.i')).is_file(), (directory, name)
            assert list(directory.glob(name + '*.optimized')), (directory, name)
print('Passed 25 thin/fat public driver output cases')
