#!/usr/bin/env python3
"""Prepare the pinned scanner and compare all precisions with host libc."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--sanitize', action='store_true')
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
pin = json.loads((ROOT / 'parse/sources.json').read_text())
source = ROOT / 'parse/floatscan.c'
if hashlib.sha256(source.read_bytes()).hexdigest() != pin['source_sha256']:
    raise SystemExit('Scanner baseline hash mismatch')
shutil.copyfile(source, out / 'floatscan.c')
subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i',
                str(ROOT / 'parse/0001-nextstep-string-input.patch')], cwd=out, check=True)
flags = ['-O2']
if a.sanitize:
    flags += ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
subprocess.run(['cc', *flags, '-I' + str(ROOT / 'parse'),
                '-Dstrtod=nextstep_strtod', '-Dstrtof=nextstep_strtof',
                '-Dstrtold=nextstep_strtold', '-c', str(out / 'floatscan.c'),
                '-o', str(out / 'parse.o')], check=True)
subprocess.run(['cc', *flags, str(ROOT / 'tests/parse-host.c'),
                str(out / 'parse.o'), '-o', str(out / 'check')], check=True)
with (out / 'results.log').open('wb') as log:
    result = subprocess.run([str(out / 'check')], stdout=log, stderr=subprocess.STDOUT)
print((out / 'results.log').read_text(), end='')
raise SystemExit(result.returncode)
