#!/usr/bin/env python3
"""Replay the pinned math adapters and run focused host checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--sanitize', action='store_true')
a = p.parse_args()
out = a.output.resolve()
if out.exists() or out == ROOT or ROOT in out.parents:
    p.error('Use a fresh output directory outside the maintained component')
out.mkdir(parents=True)
source = out / 'math'
source.mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
pin = json.loads((ROOT / 'math/sources.json').read_text())
for name, expected in pin['files_sha256'].items():
    if sha(ROOT / 'math' / name) != expected:
        p.error('Pinned math source mismatch: ' + name)
    shutil.copyfile(ROOT / 'math' / name, source / name)
shutil.copyfile(ROOT / 'math/math-support.h', source / 'math-support.h')
record = {'sanitized': a.sanitize, 'steps': [], 'sources_sha256': {
    str(path.relative_to(ROOT)): sha(path) for path in
    [*sorted((ROOT / 'math').iterdir()), ROOT / 'src/clock-realtime.c',
     ROOT / 'tests/math-clock.c', ROOT / 'tests/math-log2-vectors.h',
     ROOT / 'tests/clock-failures.c', ROOT / 'tests/math-differential.c', Path(__file__)] if path.is_file()}}
env = dict(os.environ, LC_ALL='C', ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')


def run(command, name):
    command = list(map(str, command))
    with (out / name).open('w') as stream:
        result = subprocess.run(command, cwd=source, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=30)
    record['steps'].append({'command': command, 'log': name, 'exitcode': result.returncode})
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    if result.returncode:
        raise SystemExit('Host math/clock check failed; inspect ' + str(out / name))


run(['patch', '-p1', '--batch', '--fuzz=0', '-i', ROOT / 'math/0001-nextstep-math-support.patch'], 'patch.log')
flags = [os.environ.get('CC', 'cc'), '-std=gnu17', '-O2', '-Wall', '-Wextra', '-Werror']
if a.sanitize:
    flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
run(flags + ['-fno-builtin', '-DNS33_HOST_TEST', '-I' + str(source),
             ROOT / 'tests/math-clock.c',
             *[source / name for name in ['fmin.c', 'fmax.c', 'log2.c', 'log2_data.c']],
             ROOT / 'src/clock-realtime.c', '-lm', '-o', out / 'math-clock'], 'build.log')
run([out / 'math-clock'], 'run.log')
run(flags + [ROOT / 'tests/clock-failures.c', '-o', out / 'clock-failures'], 'build-failures.log')
run([out / 'clock-failures'], 'run-failures.log')
run(flags + ['-fno-builtin', '-I' + str(source), ROOT / 'tests/math-differential.c',
             source / 'log2.c', source / 'log2_data.c', '-lm', '-o', out / 'differential'], 'build-differential.log')
run([out / 'differential'], 'run-differential.log')
record['passed'] = True
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
print((out / 'run.log').read_text().strip())
print((out / 'run-failures.log').read_text().strip())

print((out / 'run-differential.log').read_text().strip())
