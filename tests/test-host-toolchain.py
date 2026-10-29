#!/usr/bin/env python3
"""Exercise fat compile/link/archive operations and produce guest runtime inputs."""
import argparse
import json
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--driver', type=Path, default=ROOT / 'tools/nextstep-gcc')
a = p.parse_args()
D = ROOT / 'work/host-toolchain-tests'
D.mkdir(exist_ok=True)
arches = ['i386', 'm68k', 'sparc', 'hppa']
base = [str(a.driver.resolve()), '--sdk', str(a.sdk.resolve()),
        *[item for arch in arches for item in ['-arch', arch]], '-O2', '-std=gnu89']
T = ROOT / 'work/host-tools/bin'
results = []
def run(label, cmd):
    r = subprocess.run(list(map(str, cmd)), capture_output=True, text=True)
    results.append({'name': label, 'command': list(map(str, cmd)), 'exitcode': r.returncode,
                    'stdout': r.stdout, 'stderr': r.stderr})
    (D / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    if r.returncode: raise SystemExit(label + ': ' + r.stderr)
for source, name in [('runtime-c.c', 'runtime'), ('libc-smoke.c', 'libc')]:
    run(name + ' fat compile', base + ['-c', str(ROOT / 'tests' / source), '-o', str(D / (name + '.o'))])
    run(name + ' fat link', base + [str(D / (name + '.o')), '-o', str(D / name),
                                   '--build-record', str(D / (name + '-build.json'))])
(D / 'library.c').write_text('long long adjust(long long x) { return x * 97; }\n')
(D / 'archive-main.c').write_text('''#include <stdio.h>
extern long long adjust(long long);
int main(void) {
  volatile long long x = 1234567890;
  if (adjust(x) != 119753085330LL) return 1;
  puts("fat archive: passed");
  return 0;
}
''')
run('library fat compile', base + ['-c', D / 'library.c', '-o', D / 'library.o'])
run('indexed fat archive', [T / 'libtool', '-static', '-o', D / 'libprobe.a', D / 'library.o'])
run('archive index refresh', [T / 'ranlib', D / 'libprobe.a'])
run('fat archive link', base + [D / 'archive-main.c', '-L' + str(D), '-lprobe', '-o', D / 'archive-test'])
for source, language, name in [('cxx-constructors.cc', 'c++', 'cxx'),
                                ('objc-strings.m', 'objective-c', 'objc')]:
    options = [x for x in base if not x.startswith('-std=')]
    if language == 'c++': options += ['-std=gnu++98', '-fno-exceptions', '-fno-rtti']
    run(name + ' fat build', options + ['-x', language, ROOT / 'tests' / source, '-o', D / name])
# Link every runtime member, including helpers that this probe does not call.
# This checks archive closure without importing the old compiler's libcc.a.
for arch in arches:
    runtime_dir = ROOT / 'work' / ('runtime-host-' + arch)
    members = json.loads((runtime_dir / 'build-record.json').read_text())['helpers']
    single = [str(a.driver.resolve()), '--sdk', str(a.sdk.resolve()), '-arch', arch,
              '-O2', '-c', str(D / 'archive-main.c'), '-o', str(D / (arch + '-main.o'))]
    run(arch + ' closure main', single)
    # archive-main needs adjust, so include a thin library object as well.
    single[-3] = str(D / 'library.c')
    single[-1] = str(D / (arch + '-library.o'))
    run(arch + ' closure library', single)
    cmd = [T / 'ld', '-arch', arch, '-static', a.sdk.resolve() / 'lib/crt0.o',
           D / (arch + '-main.o'), D / (arch + '-library.o')]
    cmd += [runtime_dir / (row['helper'] + '.o') for row in members]
    cmd += [a.sdk.resolve() / 'lib/libsys_s.a', '-o', D / (arch + '-all-members')]
    run(arch + ' complete basic runtime closure', cmd)
for name in ['runtime', 'libc', 'archive-test', 'cxx', 'objc']:
    run(name + ' architecture audit', [T / 'lipo', D / name, '-verify_arch', *arches])
# Failed builds must not replace a previous executable.
old = digest(D / 'runtime')
r = subprocess.run(base + ['-fPIC', ROOT / 'tests/runtime-c.c', '-o', D / 'runtime'], capture_output=True)
if not r.returncode or digest(D / 'runtime') != old:
    raise SystemExit('PIC rejection/output preservation failed')
results.append({'name': 'PIC rejected and previous executable preserved', 'passed': True})
(D / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
(D / 'inputs.json').write_text(json.dumps({n: digest(D / n) for n in ['runtime','libc','archive-test','cxx','objc']}, indent=2) + '\n')
print('Host compile/link/archive checks passed. Guest execution is a separate step.')
