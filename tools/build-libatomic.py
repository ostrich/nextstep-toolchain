#!/usr/bin/env python3
"""Build optimized upstream libatomic with the native NEXTSTEP lock adapter."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
from build_inputs import digest, patch_hashes

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], required=True)
p.add_argument('--compiler-build', type=Path, required=True)
p.add_argument('--host-tools', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--jobs', type=int, default=4)
a = p.parse_args()
if a.jobs < 1:
    p.error('--jobs must be positive')
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
tools = a.host_tools.resolve()
compiler = a.compiler_build.resolve()
src = ROOT / 'work/gcc-16.2.0/libatomic'
driver = [str(ROOT / 'tools/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
          '--compiler-build', str(compiler), '--host-tools', str(tools), '-arch', a.arch]
launcher = out / 'cross-cc'
launcher.write_text('#!/bin/sh\nexec ' + shlex.join(driver) + ' "$@"\n')
launcher.chmod(0o755)
values = {'CC': str(launcher), 'CFLAGS': '-O2',
          'CPPFLAGS': '-I' + str(ROOT / 'nextstepcompat/include'),
          'AR': str(tools / 'ar'), 'RANLIB': str(tools / 'ranlib'),
          'LD': str(tools / 'ld'), 'NM': str(tools / 'nm'),
          'LIBS': '',
          'LC_ALL': 'C', 'ZERO_AR_DATE': '1'}
env = dict(os.environ, **values)
record = {'arch': a.arch, 'environment': values, 'steps': [],
          'patches_sha256': patch_hashes(ROOT),
          'compiler_sha256': {n: digest(compiler / 'gcc' / n) for n in ['xgcc', 'cc1']},
          'host_tools_sha256': {n: digest(tools / n) for n in ['ar', 'ranlib', 'ld', 'as-' + a.arch]},
          'compatibility_headers_sha256': {str(n.relative_to(ROOT)): digest(n)
              for n in sorted((ROOT / 'nextstepcompat/include').rglob('*')) if n.is_file()}}
if a.arch in ('sparc', 'hppa'):
    # Reject older compilers whose atomics cannot obey this runtime's policy.
    probe = out / 'atomic-policy.c'
    probe.write_text('_Static_assert(!__atomic_always_lock_free(4, 0), "native lock fallback");\n'
                     'void store(unsigned *p, unsigned v) { __atomic_store_n(p, v, 5); }\n')
    command = driver + ['-O2', '-S', str(probe), '-o', str(out / 'atomic-policy.s')]
    with (out / 'atomic-policy.log').open('wb') as log:
        r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    record['steps'].append({'command': command, 'exitcode': r.returncode})
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if r.returncode:
        raise SystemExit('Compiler atomic policy check failed; inspect atomic-policy.log')
    if a.arch == 'sparc' and '___atomic_store_4' not in (out / 'atomic-policy.s').read_text():
        raise SystemExit('SPARC compiler still emits stores outside the shared atomic protocol')
steps = []
if (out / 'Makefile').exists():
    steps.append(('clean', ['make', 'clean']))
steps += [('configure', [str(src / 'configure'), '--build=x86_64-pc-linux-gnu',
           '--host=' + a.arch + '-next-nextstep3.3', '--disable-shared',
           '--enable-static', '--disable-multilib', '--disable-symvers',
           '--disable-dependency-tracking']),
          # Configure needs the compatibility archive for real link probes.
          # Passing it into libtool's static build creates a nested archive
          # member instead of a usable dependency. Final links add it explicitly.
          ('build', ['make', '-j' + str(a.jobs), 'LIBS=', 'libatomic.la'])]
for name, cmd in steps:
    print(name + ': ' + str(out / (name + '.log')), flush=True)
    with (out / (name + '.log')).open('wb') as log:
        r = subprocess.run(cmd, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
    record['steps'].append({'command': cmd, 'exitcode': r.returncode})
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if r.returncode:
        raise SystemExit(name + ' failed; inspect its log')
record['artifact_sha256'] = digest(out / '.libs/libatomic.a')
(out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
print('Built libatomic; guest execution remains required.')
