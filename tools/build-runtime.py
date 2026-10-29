#!/usr/bin/env python3
"""Build optimized basic C libgcc archives using Linux-hosted target tools."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from build_inputs import digest, patch_hashes

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa', 'all'], default='all')
p.add_argument('--tools', type=Path, default=ROOT / 'work/host-tools/bin')
p.add_argument('--jobs', type=int, default=8)
p.add_argument('--output', type=Path, help='Output directory for one architecture')
p.add_argument('--compiler-build', type=Path, help='Use a separate compiler build for a single architecture')
a = p.parse_args()
if a.output and a.arch == 'all':
    p.error('--output requires one --arch')
if a.compiler_build and a.arch == 'all':
    p.error('--compiler-build requires one --arch')
if a.jobs < 1:
    p.error('--jobs must be positive')
W = ROOT / 'work'
S = W / 'gcc-16.2.0'
T = a.tools.resolve()
BASE = '''muldi3 negdi2 lshrdi3 ashldi3 ashrdi3 cmpdi2 ucmpdi2 absvsi2 absvdi2
addvsi3 addvdi3 subvsi3 subvdi3 mulvsi3 mulvdi3 negvsi2 negvdi2 ffssi2 ffsdi2
clz clzsi2 clzdi2 ctzsi2 ctzdi2 popcount_tab popcountsi2 popcountdi2 paritysi2
paritydi2 powisf2 powidf2 powixf2 bswapsi2 bswapdi2 clrsbsi2 clrsbdi2 divdi3
moddi3 divmoddi4 udivdi3 umoddi3 udivmoddi4 udiv_w_sdiv'''.split()
BASE += [op + mode + 'c3' for op in ['mul', 'div'] for mode in ['s', 'd', 'x', 't']]
FUNCS = BASE + ['fixuns' + m + 'si' for m in ['sf', 'df', 'xf']]
FUNCS += [op + mode + 'di' for op in ['fix', 'fixuns'] for mode in ['sf', 'df', 'xf']]
FUNCS += [op + 'di' + mode for op in ['float', 'floatun'] for mode in ['sf', 'df', 'xf']]
for arch in (['i386', 'm68k', 'sparc', 'hppa'] if a.arch == 'all' else [a.arch]):
    D = a.output.resolve() if a.output else W / ('runtime-host-' + arch)
    D.mkdir(parents=True, exist_ok=True)
    G = (a.compiler_build.resolve() if a.compiler_build else W / ('build-' + arch)) / 'gcc'
    (D / 'libgcc_tm.h').write_text('/* No extra target runtime definitions. */\n')
    def build(name):
        cmd = [str(G / 'xgcc'), '-B' + str(G) + '/', '-O2', '-S', '-fbuilding-libgcc',
               '-fno-stack-protector', '-Dinhibit_libc', '-DIN_LIBGCC2', '-DIN_GCC',
               '-DHAVE_CONFIG_H', '-DL_' + name, '-I' + str(D), '-I' + str(G),
               '-I' + str(S / 'gcc'), '-I' + str(S / 'include'),
               str(S / 'libgcc/libgcc2.c'), '-o', str(D / (name + '.s'))]
        c = subprocess.run(cmd, capture_output=True, text=True)
        rows = [{'command': cmd, 'exitcode': c.returncode, 'stderr': c.stderr}]
        if not c.returncode:
            cmd = [str(T / ('as-' + arch)), '-o', str(D / (name + '.o')), str(D / (name + '.s'))]
            c = subprocess.run(cmd, capture_output=True, text=True)
            rows.append({'command': cmd, 'exitcode': c.returncode, 'stderr': c.stderr})
        return {'helper': name, 'passed': c.returncode == 0, 'steps': rows}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        rows = list(pool.map(build, FUNCS))
    record = {'arch': arch, 'optimization': '-O2', 'compiler_sha256': digest(G / 'cc1'),
              'patches_sha256': patch_hashes(ROOT), 'source_sha256': digest(S / 'libgcc/libgcc2.c'),
              'assembler_sha256': digest(T / ('as-' + arch)), 'helpers': rows}
    failed = [r for r in rows if not r['passed']]
    if not failed:
        # Explicit objects prevent stale archive members surviving a rebuild.
        archive = D / 'libgcc.a'
        archive.unlink(missing_ok=True)
        cmd = [str(T / 'libtool'), '-static', '-o', str(archive),
               *[str(D / (name + '.o')) for name in FUNCS]]
        c = subprocess.run(cmd, capture_output=True, text=True)
        record['archive'] = {'command': cmd, 'exitcode': c.returncode, 'stderr': c.stderr}
        if not c.returncode:
            record['archive_sha256'] = digest(archive)
    (D / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if failed:
        raise SystemExit('\n'.join(r['steps'][-1]['stderr'] for r in failed))
    if c.returncode:
        raise SystemExit(c.stderr)
    print(arch + ': built ' + str(len(FUNCS)) + ' runtime members', flush=True)
