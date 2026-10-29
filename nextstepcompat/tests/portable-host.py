#!/usr/bin/env python3
"""Sanitize portable string implementations and environment ownership on host.

Native FILE adapters and line input require the separate NeXT guest tests.
Host time and intmax/line-input calls in the fixtures remain host-libc controls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
pins = json.loads((ROOT / 'string/sources.json').read_text())
for name, expected in pins['files_sha256'].items():
    if hashlib.sha256((ROOT / 'string' / name).read_bytes()).hexdigest() != expected:
        p.error('String input checksum mismatch: ' + name)
names = ['memcmp', 'strcmp', 'strncmp', 'strdup', 'strndup', 'strnlen', 'strtok_r', 'strstr', 'setenv', 'unsetenv', 'putenv']
flags = ['-D' + n + '=ns33_host_' + n for n in names]
sources = [*(ROOT / 'string' / n for n in pins['files_sha256'] if n.endswith('.c')),
           ROOT / 'src/environment.c']
results = []
for test in ['memory_boundaries', 'portable_apis', 'environment_time']:
    executable = out / test
    command = ['cc', '-O2', '-g', '-std=gnu99', '-fno-builtin', '-fno-omit-frame-pointer',
               '-fsanitize=address,undefined', *flags, *map(str, sources),
               str(ROOT / 'tests/coverage' / (test + '.c')), '-o', str(executable)]
    build = subprocess.run(command, capture_output=True)
    (out / (test + '-build.log')).write_bytes(build.stdout + build.stderr)
    if build.returncode:
        raise SystemExit('Build failed: ' + test)
    # External replacement of environ intentionally abandons the previous
    # exported pointer table, as documented. Its lifetime cannot be inferred
    # from the replacement. This tests memory safety, not a no-leaks contract.
    run = subprocess.run([str(executable)], capture_output=True, timeout=30,
                         env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0', 'UBSAN_OPTIONS': 'halt_on_error=1'})
    (out / (test + '.log')).write_bytes(run.stdout + run.stderr)
    results.append({'test': test, 'exitcode': run.returncode, 'command': command})
(out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
if any(r['exitcode'] for r in results):
    raise SystemExit('Host memory-safety checks failed; inspect logs')
print('Three host memory-safety programs passed; native FILE behavior remains guest-only.')
