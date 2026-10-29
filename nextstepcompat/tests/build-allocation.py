#!/usr/bin/env python3
"""Build optimized NIHS allocation probes using a staged compiler bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--shared', type=Path, help='Canonical shared component build')
a = p.parse_args()
tc, out = a.toolchain.resolve(), a.output.resolve()
if out.exists(): p.error('Use a fresh output directory')
out.mkdir(parents=True)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
record = {'toolchain_manifest_sha256': digest(tc / 'toolchain.json'),
          'sources_sha256': {}, 'steps': [], 'artifacts_sha256': {}}
try:
    for name in ['allocation-native', 'allocation-faults', 'allocator-guards']:
        source = ROOT / 'tests' / (name + '.c')
        record['sources_sha256'][source.name] = digest(source)
        slices = []
        for arch in ['m68k', 'i386', 'hppa', 'sparc']:
            target = out / (name + '-' + arch)
            cmd = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
                   '-arch', arch, '-O2', str(source)]
            if a.shared and name != 'allocator-guards':
                cmd += [str(a.shared.resolve() / 'libnextstepcompat.a')]
            cmd += ['-o', str(target)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            record['steps'].append({'command': cmd, 'exitcode': r.returncode,
                                    'stdout': r.stdout, 'stderr': r.stderr})
            if r.returncode: raise RuntimeError(r.stderr)
            slices.append(str(target))
        subprocess.run([str(tc / 'libexec/cctools/lipo'), '-create', *slices,
                        '-output', str(out / name)], check=True)
        record['artifacts_sha256'][name] = digest(out / name)
    record['status'] = 'built'
finally:
    (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
