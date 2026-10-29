#!/usr/bin/env python3
"""Build classic startup-table regressions and reject unsupported strip targets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
tc, sdk, out = [n.resolve() for n in [a.toolchain, a.sdk, a.output]]
if out.exists(): p.error('Use a fresh output directory')
out.mkdir(parents=True)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
source = ROOT / 'tests/dead-strip-startup.c'
record = {'source_sha256': digest(source), 'toolchain_manifest_sha256': digest(tc / 'toolchain.json'), 'targets': {}}
slices = []
try:
    for arch in ['m68k', 'i386', 'hppa', 'sparc']:
        target = out / ('startup-' + arch)
        cc = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch, '-O2']
        steps = []; record['targets'][arch] = {'steps': steps}
        if arch in ['hppa', 'sparc']:
            cmd = cc + ['-Wl,-dead_strip', str(source), '-o', str(out / ('unsupported-' + arch))]
            r = subprocess.run(cmd, capture_output=True, text=True)
            steps.append({'command': cmd, 'exitcode': r.returncode, 'stderr': r.stderr})
            assert r.returncode and '-dead_strip not supported' in r.stderr, r.stderr
            assert not (out / ('unsupported-' + arch)).exists()
        cmd = cc + (['-Wl,-dead_strip'] if arch in ['m68k', 'i386'] else []) + [str(source), '-o', str(target)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        steps.append({'command': cmd, 'exitcode': r.returncode, 'stderr': r.stderr})
        assert r.returncode == 0, r.stderr
        if arch in ['m68k', 'i386']:
            syms = subprocess.check_output([str(tc / 'libexec/cctools/nm'), str(target)], text=True)
            assert '_ns33_unreachable_dead_strip_probe' not in syms, syms
            record['targets'][arch]['unreachable_function_removed'] = True
        record['targets'][arch]['executable_sha256'] = digest(target)
        slices.append(str(target))
    subprocess.run([str(tc / 'libexec/cctools/lipo'), '-create', *slices, '-output', str(out / 'startup')], check=True)
    script = out / 'run-codecs.sh'
    script.write_text('#!/bin/sh\ncd "$1" || exit 90\n./startup || exit 1\necho "PASS startup-table batch complete"\n')
    assets = {n: str(out / n) for n in ['startup', 'run-codecs.sh']}
    suite = {'libraries': {}, 'assets': assets, 'entry': 'run-codecs.sh',
             'success_marker': 'PASS startup-table batch complete',
             'sha256': {n: digest(Path(f)) for n, f in assets.items()}}
    (out / 'suite.json').write_text(json.dumps(suite, indent=2) + '\n')
    record['status'] = 'built'
finally:
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
