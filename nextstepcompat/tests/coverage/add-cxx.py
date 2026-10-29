#!/usr/bin/env python3
"""Add existing C++ integration gates linked against a new component build."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--compat-build', type=Path, required=True)
a = p.parse_args()
out, tc, sdk, build = (x.resolve() for x in (a.output, a.toolchain, a.sdk, a.compat_build))
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = json.loads((out / 'build-results.json').read_text())
if digest(tc / 'toolchain.json') != record['toolchain_manifest_sha256']:
    p.error('Installed bundle differs from the audit build')
for arch, modes in record['results'].items():
    library = build / arch / 'libnextstepcompat.a'
    if digest(library) != record['compatibility_build']['libraries_sha256'][arch]:
        p.error('Component archive differs from the audit build')
    for name in ['stdlib', 'numeric-cxx', 'c99-cxx']:
        key = 'cxx-' + name
        if key in modes['compat']['tests']:
            p.error('C++ regression already exists: ' + key)
        source = ROOT / 'tests/cxx-runtime' / (name + '.cc')
        libs = [tc / 'lib' / arch / n for n in ['libstdc++.a', 'libgcc_eh.a',
                'libnextstep-cxx-compat.a', 'libatomic.a', 'libnextstep-cxx-compat.a']]
        libs += [library, tc / 'lib' / arch / 'libgcc.a', sdk / 'lib/libsys_s.a']
        cmd = [str(tc / 'bin/nextstep-g++'), '--sdk', str(sdk), '-arch', arch,
               '-O2', '-std=gnu++17', '--compat-headers', str(ROOT / 'nextstepcompat/include'),
               '-nodefaultlibs', str(source), *map(str, libs), '-o', str(out / arch / ('compat-' + key))]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        (out / arch / 'compat' / (key + '-test-build.log')).write_bytes(r.stdout + r.stderr)
        if r.returncode:
            p.error('C++ regression build failed: ' + arch + '/' + name)
        modes['compat']['tests'][key] = {'kind': 'guest-regression', 'build': 'passed',
            'run': 'untested', 'command': cmd, 'source_sha256': digest(source),
            'arguments': ['/private/tmp', '/bin/sh'] if name == 'stdlib' else []}
(out / 'build-results.json').write_text(json.dumps(record, indent=2) + '\n')
print('Added three C++ integration regressions per target')
