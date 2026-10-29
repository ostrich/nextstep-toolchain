#!/usr/bin/env python3
"""Build a hashed NIHS binary64 trunc runtime suite."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'compat', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--shared', action='store_true')
a = p.parse_args()
tc, sdk, compat, out = [x.resolve() for x in [a.toolchain, a.sdk, a.compat, a.output]]
if out.exists(): p.error('Use a fresh output directory')
out.mkdir(parents=True)
record = {'steps': [], 'toolchain_manifest_sha256': hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest()}
for arch in ['m68k', 'i386', 'hppa', 'sparc']:
    library = compat / 'libnextstepcompat.a' if a.shared else compat / arch / 'libnextstepcompat.a'
    cmd = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '--compat-headers', str(ROOT / 'include'),
           '-arch', arch, '-O2', str(ROOT / 'tests/trunc.c'), str(library), '-o', str(out / ('trunc-' + arch))]
    subprocess.run(cmd, check=True); record['steps'].append(cmd)
subprocess.run([str(tc / 'libexec/cctools/lipo'), '-create',
                *[str(out / ('trunc-' + arch)) for arch in ['m68k', 'i386', 'hppa', 'sparc']],
                '-output', str(out / 'trunc')], check=True)
(out / 'run-codecs.sh').write_text('#!/bin/sh\nset -e\n./trunc\necho PASS trunc batch complete\n')
suite = {'libraries': {}, 'assets': {n: str(out / n) for n in ['trunc', 'run-codecs.sh']},
         'entry': 'run-codecs.sh', 'success_marker': 'PASS trunc batch complete'}
if a.shared: suite['libraries']['libnextstepcompat.1.shlib'] = str(compat / 'libnextstepcompat.1.shlib')
suite['sha256'] = {n: hashlib.sha256(Path(source).read_bytes()).hexdigest()
                   for n, source in {**suite['assets'], **suite['libraries']}.items()}
(out / 'suite.json').write_text(json.dumps(suite, indent=2) + '\n')
(out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
