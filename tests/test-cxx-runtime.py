#!/usr/bin/env python3
"""Build the C++ runtime fixture. Guest execution remains a separate step."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', required=True, type=Path)
p.add_argument('--compiler-build', required=True, type=Path)
p.add_argument('--runtime-build', required=True, type=Path)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
p.add_argument('--output', required=True, type=Path)
p.add_argument('--suite', choices=['abi', 'stdlib', 'format', 'threads', 'atomics'], default='abi')
p.add_argument('--atomic-build', type=Path, help='Built upstream libatomic directory')
p.add_argument('--host-tools', type=Path)
p.add_argument('--use-cxa-atexit', action='store_true', help='Exercise modern C++ cleanup registration')
p.add_argument('--fault-diagnostics', action='store_true', help='Install test-only native signal capture before library constructors')
a = p.parse_args()
if a.suite == 'atomics' and not a.atomic_build:
    p.error('--suite atomics requires --atomic-build')
diagnostic_record = None
b = a.runtime_build.resolve()
s = ROOT / 'work/gcc-16.2.0'
output = a.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
command = [str(ROOT / 'tools/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
           '--compiler-build', str(a.compiler_build.resolve()), '-arch', a.arch,
           '-O2', '-std=gnu11' if a.suite == 'format' else '-std=gnu++17']
if a.use_cxa_atexit:
    command += ['-fuse-cxa-atexit']
if a.host_tools:
    command += ['--host-tools', str(a.host_tools.resolve())]
command += ['-I' + str(x) for x in [b / 'include', b / ('include/' + a.arch + '-next-nextstep3.3'),
            s / 'libstdc++-v3/libsupc++', ROOT / 'nextstepcompat/include']]
names = {'abi': ['main.cc', 'throw.cc'], 'stdlib': ['stdlib.cc'], 'format': ['format.c'], 'threads': ['threads.cc'], 'atomics': ['atomics.cc']}[a.suite]
if a.fault_diagnostics:
    if a.arch not in ('sparc', 'hppa'):
        p.error('--fault-diagnostics currently supports sparc and hppa')
    diagnostic = output.with_suffix('.diagnostic.o')
    compile_diagnostic = command[:command.index('-std=gnu11' if a.suite == 'format' else '-std=gnu++17')]
    compile_diagnostic += ['-c', str(ROOT / 'tests/cxx-runtime/fault-diagnostic.c'), '-o', str(diagnostic)]
    if a.host_tools:
        compile_diagnostic += ['--host-tools', str(a.host_tools.resolve())]
    if a.suite == 'stdlib':
        compile_diagnostic += ['-DTEST_LOCALE_STATE']
    subprocess.run(compile_diagnostic, check=True)
    diagnostic_source = ROOT / 'tests/cxx-runtime/fault-diagnostic.c'
    diagnostic_record = {'command': compile_diagnostic,
                         'source_sha256': hashlib.sha256(diagnostic_source.read_bytes()).hexdigest()}
    command += [str(diagnostic)]
command += [str(b / 'crt-nextstep.o')]
command += [str(ROOT / 'tests/cxx-runtime' / name) for name in names]
standard_library = b / ('libsupc++/.libs/libsupc++.a' if a.suite not in ('stdlib', 'threads', 'atomics') else 'src/.libs/libstdc++.a')
command += [str(standard_library), str(b / 'libgcc_eh.a'),
            str(b / 'libnextstep-cxx-compat.a')]
if a.atomic_build:
    command += [str(a.atomic_build.resolve() / '.libs/libatomic.a')]
command += [str(b / 'nextstepcompat' / a.arch / 'libnextstepcompat.a')]
command += ['-o', str(output),
            '--build-record', str(output.with_suffix('.build.json'))]
with output.with_suffix('.log').open('wb') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    raise SystemExit('Fixture build failed; inspect ' + str(output.with_suffix('.log')))
record_path = output.with_suffix('.build.json')
record = json.loads(record_path.read_text())
record['fixture'] = {'suite': a.suite, 'fault_diagnostic': diagnostic_record}
record_path.write_text(json.dumps(record, indent=2) + '\n')
print('Built ' + str(output) + '; not yet guest-tested.')
