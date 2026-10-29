#!/usr/bin/env python3
"""Build pinned upstream re2c as a substantial C++ runtime execution fixture."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], required=True)
p.add_argument('--toolchain', type=Path, help='Installed coherent compiler/runtime bundle')
p.add_argument('--compiler-build', type=Path)
p.add_argument('--runtime-build', type=Path)
p.add_argument('--host-tools', type=Path)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--cases', type=Path, help='Prepared complete-output cases; also build the guest runner')
p.add_argument('--atomic-build', type=Path, help='Matching upstream libatomic directory')
a = p.parse_args()
if a.jobs < 1:
    p.error('--jobs must be positive')
if a.toolchain:
    if any([a.compiler_build, a.runtime_build, a.host_tools, a.atomic_build]):
        p.error('Use either an installed bundle or development build paths')
elif not all([a.compiler_build, a.runtime_build, a.host_tools]):
    p.error('Provide --toolchain or all three development build paths')
pin = json.loads((ROOT / 'tests/cxx-runtime/re2c-source.json').read_text())
archive = ROOT / ('work/downloads/re2c-' + pin['version'] + '.tar.xz')
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists():
    urllib.request.urlretrieve(pin['url'], archive)
if hashlib.sha256(archive.read_bytes()).hexdigest() != pin['sha256']:
    raise SystemExit('re2c archive hash mismatch')
src = ROOT / ('work/app-sources/re2c-' + pin['version'])
if not src.exists():
    with tarfile.open(archive) as t:
        t.extractall(src.parent, filter='data')
# Refuse a previously modified source tree, rather than silently claiming an
# upstream baseline merely because the downloaded archive still matches.
with tarfile.open(archive) as t:
    for member in t:
        if member.isfile():
            path = src.parent / member.name
            original = t.extractfile(member).read()
            if not path.is_file() or path.read_bytes() != original:
                raise SystemExit('Modified upstream source: ' + str(path))
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
b = a.runtime_build.resolve() if a.runtime_build else None
config = ('#define PACKAGE_VERSION "' + pin['version'] + '"\n' +
          ''.join('#define HAVE_' + h + ' 1\n' for h in
                  ['FCNTL_H', 'SYS_STAT_H', 'SYS_TYPES_H', 'UNISTD_H']))
(out / 'config.h').write_text(config)
if a.toolchain:
    common = [str(a.toolchain.resolve() / 'bin/nextstep-g++'), '--sdk', str(a.sdk.resolve())]
else:
    common = [str(ROOT / 'tools/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
          '--compiler-build', str(a.compiler_build.resolve()),
          '--host-tools', str(a.host_tools.resolve())]
common += ['-arch', a.arch,
          '-O2', '-std=gnu++11', '-DRE2C_STDLIB_DIR="/usr/local/share/re2c/stdlib/"']
includes = [out, src / 'bootstrap', src]
if b:
    includes += [b / 'include',
           b / ('include/' + a.arch + '-next-nextstep3.3'),
           ROOT / 'work/gcc-16.2.0/libstdc++-v3/libsupc++',
           ROOT / 'nextstepcompat/include']
common += ['-I' + str(x) for x in includes]
makefile = (src / 'Makefile.am').read_text()
def sources(variable):
    match = re.search(r'^' + variable + r' = \\\n((?:\t.*\n)+)', makefile, re.M)
    if not match:
        raise SystemExit('Cannot find upstream source list: ' + variable)
    return re.findall(r'src/[A-Za-z0-9_/]+\.cc', match.group(1))
names = ['src/main.cc'] + sources('re2c_SRC')
names += sources('re2c_GEN_SRC') + ['src/msg/help_re2c.cc']
def compile_one(name):
    source = src / name
    if not source.exists():
        source = src / 'bootstrap' / name
    obj = out / (name.replace('/', '_') + '.o')
    command = common + ['-c', str(source), '-o', str(obj),
                        '--build-record', str(obj.with_suffix('.json'))]
    with obj.with_suffix('.log').open('wb') as log:
        r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError('Compilation failed: ' + str(obj.with_suffix('.log')))
    return obj
with ThreadPoolExecutor(max_workers=a.jobs) as pool:
    objects = list(pool.map(compile_one, names))
command = common + [str(o) for o in objects]
if b:
    command += [str(b / 'crt-nextstep.o'), str(b / 'src/.libs/libstdc++.a'), str(b / 'libgcc_eh.a'),
            str(b / 'libnextstep-cxx-compat.a'),
            str(b / 'nextstepcompat' / a.arch / 'libnextstepcompat.a')]
if a.atomic_build:
    command += [str(a.atomic_build.resolve() / '.libs/libatomic.a')]
command += ['-o', str(out / 're2c'),
            '--build-record', str(out / 'link.json')]
with (out / 'link.log').open('wb') as log:
    r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
if r.returncode:
    raise SystemExit('Link failed: ' + str(out / 'link.log'))
(out / 'application.json').write_text(json.dumps({
    'upstream': pin, 'arch': a.arch, 'source_files': names,
    'config_h': config, 'optimization': '-O2',
    'executable_sha256': hashlib.sha256((out / 're2c').read_bytes()).hexdigest(),
    'execution_status': 'not tested'}, indent=2) + '\n')
print('Built upstream re2c from ' + str(len(names)) + ' C++ units; guest execution required.')
if a.cases:
    runner = [x.replace('-std=gnu++11', '-std=gnu11') for x in common]
    if a.toolchain:
        runner[0] = str(a.toolchain.resolve() / 'bin/nextstep-gcc')
    runner += ['-I' + str(a.cases.resolve()),
               str(ROOT / 'tests/cxx-runtime/re2c-runner.c'),
               '-o', str(out / 're2c-runner'),
               '--build-record', str(out / 'runner.json')]
    with (out / 'runner.log').open('wb') as log:
        r = subprocess.run(runner, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode:
        raise SystemExit('Runner build failed: ' + str(out / 'runner.log'))
    print('Built guest application runner.')
