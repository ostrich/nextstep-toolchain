#!/usr/bin/env python3
"""Add reduced native controls and existing guest regressions to an API audit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--compat-build', type=Path, help='Separate component build; default is the installed bundle')
p.add_argument('--test', action='append', help='Add only these named regression programs')
a = p.parse_args()
out, tc, sdk = [x.resolve() for x in (a.output, a.toolchain, a.sdk)]
lib = a.compat_build.resolve() if a.compat_build else None
manifest = json.loads((tc / 'toolchain.json').read_text())
record = json.loads((out / 'build-results.json').read_text())
if hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest() != record['toolchain_manifest_sha256']:
    p.error('Toolchain differs from the audit build')
for arch, modes in record['results'].items():
    library = (lib / arch / 'libnextstepcompat.a') if lib else tc / 'lib' / arch / 'libnextstepcompat.a'
    expected = record['compatibility_build']['libraries_sha256'][arch] if lib else manifest['files']['lib/' + arch + '/libnextstepcompat.a']
    if hashlib.sha256(library.read_bytes()).hexdigest() != expected:
        p.error('Compatibility library differs from the audit build')
    for mode, data in modes.items():
        names = ['regressions']
        if mode == 'compat':
            names += ['smoke', 'singlebyte', 'regex', 'allocation', 'signals', 'fifo', 'groups', 'line-faults', 'allocation-faults']
        if a.test:
            unknown = set(a.test) - {'regressions', 'smoke', 'singlebyte', 'regex', 'allocation', 'signals', 'fifo', 'groups', 'line-faults', 'allocation-faults'}
            if unknown:
                p.error('Unknown regression: ' + ', '.join(sorted(unknown)))
            names = [name for name in names if name in a.test]
        for name in names:
            if name in data['tests']:
                p.error('Regression already added: ' + arch + '/' + mode + '/' + name)
            source = HERE.parent / ('libc-regressions.c' if name == 'regressions' else name + '.c')
            dest = out / arch / (mode + '-' + name)
            cmd = [sys.executable, str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk),
                   '-arch', arch, '-O2', '-fno-builtin']
            if mode == 'native':
                cmd += ['--compat-headers', str(out / 'native-headers'), '-nodefaultlibs']
            elif lib:
                cmd += ['--compat-headers', str(HERE.parents[1] / 'include'), '-nodefaultlibs']
            if mode == 'compat' and name == 'regressions':
                cmd += ['-DNS33_EXTENDED']
            cmd += [str(source)]
            if mode == 'compat' and lib:
                cmd += [str(library)]
            if mode == 'native' or lib:
                cmd += [str(tc / 'lib' / arch / 'libgcc.a'), str(sdk / 'lib/libsys_s.a')]
            cmd += ['-o', str(dest)]
            r = subprocess.run(cmd, capture_output=True, timeout=90)
            (out / arch / mode / (name + '-test-build.log')).write_bytes(r.stdout + r.stderr)
            data['tests'][name] = {'kind': 'guest-regression', 'build': 'passed' if r.returncode == 0 else 'failed',
                                   'run': 'untested', 'command': cmd,
                                   'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            if r.returncode:
                p.error('Regression build failed: ' + arch + '/' + mode + '/' + name)
(out / 'build-results.json').write_text(json.dumps(record, indent=2) + '\n')
print('Added selected regression builds; see build-results.json for the exact programs')
