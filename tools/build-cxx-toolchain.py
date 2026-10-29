#!/usr/bin/env python3
"""Build the four-target C++ snapshot in the checked-in build-set order."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--jobs', type=int, default=4, help='Jobs per target')
p.add_argument('--parallel-targets', type=int, default=1)
p.add_argument('--build-set', type=Path, default=ROOT / 'toolchain/cxx-build-set.json')
a = p.parse_args()
if a.jobs < 1 or not 1 <= a.parallel_targets <= 4:
    p.error('Positive --jobs and 1..4 --parallel-targets are required')
configuration = json.loads(a.build_set.read_text())
if set(configuration['targets']) != {'i386', 'm68k', 'sparc', 'hppa'}:
    p.error('Build set must describe all four targets')
logs = ROOT / 'work/cxx-runtime/snapshot-build'
logs.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(ROOT / 'tools/verify-patches.py')], check=True)
sdk = str(a.sdk.resolve())
host = ROOT / configuration['host_tools']
if not (host / 'build-record.json').is_file():
    raise SystemExit('Build the pinned host tools in ' + str(host) + ' first.')

def build_target(item):
    arch, paths = item
    # The basic builder's stable directory is also the link driver's bootstrap
    # libgcc location. The checked-in build set uses that same directory.
    if paths['basic_runtime'] != 'work/runtime-host-' + arch:
        raise RuntimeError('Unsupported bootstrap libgcc location: ' + arch)
    commands = [
        ('compiler', ['build.py', '--arch', arch, '--languages', 'c,c++,objc,obj-c++',
          '--exception-model', 'sjlj', '--thread-model', 'nextstep',
          '--output', paths['compiler'], '--jobs', str(a.jobs)]),
        ('basic', ['build-runtime.py', '--arch', arch, '--compiler-build', paths['compiler'],
          '--tools', str(host / 'bin'), '--jobs', str(a.jobs)]),
        ('atomic', ['build-libatomic.py', '--sdk', sdk, '--arch', arch,
          '--compiler-build', paths['compiler'], '--host-tools', str(host / 'bin'),
          '--output', paths['atomic_runtime'], '--jobs', str(a.jobs)]),
        ('cxx', ['build-cxx-runtime.py', '--sdk', sdk, '--arch', arch,
          '--compiler-build', paths['compiler'], '--host-tools', str(host / 'bin'),
          '--atomic-build', paths['atomic_runtime'], '--output', paths['cxx_runtime'],
          '--phase', 'all', '--jobs', str(a.jobs)])]
    records = []
    for name, arguments in commands:
        command = [sys.executable, str(ROOT / 'tools' / arguments[0]), *arguments[1:]]
        print(arch + ': ' + name, flush=True)
        with (logs / (arch + '-' + name + '.log')).open('wb') as log:
            r = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        records.append({'phase': name, 'command': command, 'exitcode': r.returncode})
        (logs / (arch + '.json')).write_text(json.dumps(records, indent=2) + '\n')
        if r.returncode:
            raise RuntimeError(arch + ' ' + name + ' failed; inspect ' + str(logs))
    return arch

with ThreadPoolExecutor(max_workers=a.parallel_targets) as pool:
    for arch in pool.map(build_target, configuration['targets'].items()):
        print('Built complete optimized runtime: ' + arch, flush=True)
print('Build completed. Stage and execute guest regressions separately.')
