#!/usr/bin/env python3
"""Exercise the installed driver and emit guest fixtures.

The relocation check temporarily renames the compiler installation. Do not
run this test concurrently with builds using the same prefix.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--flatc-cases', type=Path)
p.add_argument('--re2c-cases', type=Path)
a = p.parse_args()
prefix, sdk, out = a.prefix.resolve(), a.sdk.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
arches = ['i386', 'm68k', 'sparc', 'hppa']
driver = prefix / 'bin/nextstep-g++'
tools = prefix / 'libexec/cctools'
base = [str(driver), '--sdk', str(sdk), '-O2', '-std=gnu++17']
base += [item for arch in arches for item in ['-arch', arch]]
results = []
def run(name, command):
    r = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    results.append({'name': name, 'command': list(map(str, command)),
                    'exitcode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
    (out / 'host-results.json').write_text(json.dumps(results, indent=2) + '\n')
    if r.returncode:
        raise SystemExit(name + ' failed; inspect host-results.json')
    return r

manifest = json.loads((prefix / 'toolchain.json').read_text())
for name, expected in manifest['files'].items():
    path = prefix / name
    if not path.resolve().is_relative_to(prefix):
        raise SystemExit('Installed file escapes bundle: ' + name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Installed file integrity failed: ' + name)
for name, target in manifest['symlinks'].items():
    if (prefix / name).readlink() != Path(target):
        raise SystemExit('Installed symlink integrity failed: ' + name)

fixture = ROOT / 'tests/cxx-runtime'
guest_names = []
for name, files in [('abi', ['main.cc', 'throw.cc']), ('stdlib', ['stdlib.cc']),
                    ('threads', ['threads.cc']), ('atomics', ['atomics.cc']),
                    ('numeric-cxx', ['numeric-cxx.cc']), ('c99-cxx', ['c99-cxx.cc'])]:
    run(name + ' fat link', base + [fixture / f for f in files] +
        ['-o', out / name, '--build-record', out / (name + '.json')])
    run(name + ' architecture audit', [tools / 'lipo', out / name, '-verify_arch', *arches])
    for arch in arches:
        target = out / arch
        target.mkdir(exist_ok=True)
        run(name + ' ' + arch + ' extraction',
            [tools / 'lipo', out / name, '-thin', arch, '-output', target / name])
    guest_names.append(name)

for source in ['main', 'throw']:
    run(source + ' fat object', base + ['-c', fixture / (source + '.cc'), '-o', out / (source + '.o')])
run('C++ objects-only link', base + [out / 'main.o', out / 'throw.o', '-o', out / 'objects-only'])
run('ordinary C link', [prefix / 'bin/nextstep-gcc', '--sdk', sdk, '-O2',
    *[item for arch in arches for item in ['-arch', arch]],
    ROOT / 'tests/libc-smoke.c', '-o', out / 'c-smoke'])
run('Objective-C++ fat link', base + ['-x', 'objective-c++', ROOT / 'tests/objc-strings.m',
                                     '-o', out / 'objcxx'])
for name in ['objects-only', 'c-smoke', 'objcxx']:
    run(name + ' architecture audit', [tools / 'lipo', out / name, '-verify_arch', *arches])
    for arch in arches:
        run(name + ' ' + arch + ' extraction',
            [tools / 'lipo', out / name, '-thin', arch, '-output', out / arch / name])
    guest_names.append(name)

c_fixtures = [('floating-conversion', []), ('floating-immediates', []),
              ('runtime-batch', []), ('nextstepcompat', []), ('singlebyte', []),
              ('signals', []), ('fifo', [])]
for name, directory in [('flatc-runner', a.flatc_cases), ('re2c-runner', a.re2c_cases)]:
    if directory:
        c_fixtures.append((name, ['-I' + str(directory.resolve())]))
for name, flags in c_fixtures:
    run(name + ' fat C link', [prefix / 'bin/nextstep-gcc', '--sdk', sdk, '-O2',
        *[item for arch in arches for item in ['-arch', arch]], *flags,
        (ROOT / 'nextstepcompat/tests/smoke.c' if name == 'nextstepcompat'
         else ROOT / 'nextstepcompat/tests' / (name + '.c') if name in ('singlebyte', 'signals', 'fifo')
         else fixture / (name + '.c')), '-o', out / name,
        '--build-record', out / (name + '.json')])
    run(name + ' architecture audit', [tools / 'lipo', out / name, '-verify_arch', *arches])
    for arch in arches:
        run(name + ' ' + arch + ' extraction',
            [tools / 'lipo', out / name, '-thin', arch, '-output', out / arch / name])
    guest_names.append(name)

(out / 'invalid.cc').write_text('this is deliberately invalid C++\n')
old = hashlib.sha256((out / 'abi').read_bytes()).hexdigest()
r = subprocess.run(base + [str(out / 'invalid.cc'), '-o', str(out / 'abi')], capture_output=True)
if not r.returncode or hashlib.sha256((out / 'abi').read_bytes()).hexdigest() != old:
    raise SystemExit('Failed compilation replaced an existing output')
results.append({'name': 'failed compilation preserves output', 'passed': True})

# Exercise actual relocation, then restore the original prefix even on failure.
relocated = prefix.with_name(prefix.name + '-relocation-test')
if relocated.exists():
    raise SystemExit('Relocation test destination already exists')
prefix.rename(relocated)
try:
    run('relocated fat C++ link', [str(relocated / 'bin/nextstep-g++'), *base[1:],
        fixture / 'main.cc', fixture / 'throw.cc', '-o', out / 'relocated'])
finally:
    relocated.rename(prefix)
if hashlib.sha256((out / 'relocated').read_bytes()).hexdigest() != old:
    raise SystemExit('Relocation changed the generated executable')
(out / 'host-results.json').write_text(json.dumps(results, indent=2) + '\n')
(out / 'guest-inputs.json').write_text(json.dumps({arch: {
    name: hashlib.sha256((out / arch / name).read_bytes()).hexdigest()
    for name in guest_names}
    for arch in arches}, indent=2) + '\n')
print('Installed-driver host checks passed; extracted slices still require guest execution.')
