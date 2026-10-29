#!/usr/bin/env python3
"""Build the isolated optimized NIHS sysconf regression and guest suite."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--shared', type=Path, help='Test a constructed shared runtime instead of isolated source')
a = p.parse_args()
tc, sdk, out = a.toolchain.resolve(), a.sdk.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
shared = a.shared.resolve() if a.shared else None
sources = [root / 'tests/sysconf.c']
if not shared:
    sources.insert(0, root / 'src/sysconf.c')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
record = {'toolchain_manifest_sha256': sha(tc / 'toolchain.json'),
          'sources_sha256': {str(s.relative_to(root)): sha(s) for s in sources},
          'targets': {}}
for arch in ['i386', 'm68k', 'hppa', 'sparc']:
    cmd = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch,
           '-O2', *map(str, sources),
           *([str(shared / 'libnextstepcompat.a')] if shared else []),
           '-o', str(out / arch)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (arch + '.log')).write_bytes(r.stdout)
    record['targets'][arch] = {'command': cmd, 'exitcode': r.returncode}
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if r.returncode:
        raise SystemExit('Build failed: ' + str(out / (arch + '.log')))
subprocess.run([str(tc / 'libexec/cctools/lipo'), '-create',
                *[str(out / arch) for arch in record['targets']],
                '-output', str(out / 'sysconf-test')], check=True)
script = out / 'run-codecs.sh'
script.write_text('#!/bin/sh\nset -e\n./sysconf-test\n')
assets = {'sysconf-test': str(out / 'sysconf-test'), 'run-codecs.sh': str(script)}
libraries = {'libnextstepcompat.1.shlib': str(shared / 'libnextstepcompat.1.shlib')} if shared else {}
suite = {'libraries': libraries, 'assets': assets, 'entry': 'run-codecs.sh',
         'success_marker': 'PASS sysconf:',
         'sha256': {name: sha(Path(path)) for name, path in {**assets, **libraries}.items()}}
(out / 'suite.json').write_text(json.dumps(suite, indent=2) + '\n')
print('Built optimized NIHS sysconf suite:', out)
