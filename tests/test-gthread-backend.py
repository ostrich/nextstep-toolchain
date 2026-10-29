#!/usr/bin/env python3
"""Build optimized native threading foundation tests without libstdc++."""
import argparse
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', required=True, choices=['i386', 'm68k', 'sparc', 'hppa'])
p.add_argument('--sdk', required=True, type=Path)
p.add_argument('--compiler-build', required=True, type=Path)
p.add_argument('--host-tools', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
output = a.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
source = ROOT / 'work/gcc-16.2.0'
command = [str(ROOT / 'tools/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
           '-arch', a.arch, '--compiler-build', str(a.compiler_build.resolve()),
           '--host-tools', str(a.host_tools.resolve()), '-O2', '-Wall', '-Wextra',
           '-I' + str(source / 'libgcc'), '-I' + str(ROOT / 'nextstepcompat/include'),
           str(ROOT / 'runtime/fp-startup.c'), str(ROOT / 'runtime/threads/cthreads.c'),
           str(ROOT / 'tests/cxx-runtime/gthread.c'), '-o', str(output),
           '--build-record', str(output.with_suffix('.build.json'))]
if a.arch == 'hppa':
    command += [str(source / 'libgcc/config/pa/sync-libfuncs.c')]
with output.with_suffix('.log').open('wb') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
print('Built ' + str(output) + '; guest execution remains required.')
