#!/usr/bin/env python3
"""Require multiple shared import closures to link independently of library order."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'iconv', 'lzo', 'compat', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args(); tc, sdk, out = [n.resolve() for n in [a.toolchain, a.sdk, a.output]]
if out.exists(): p.error('Use a fresh output directory')
out.mkdir(parents=True)
source = ROOT / 'tests/shared-libraries/import-minor-diamond.c'
libraries = [a.iconv.resolve() / 'libiconv.a', a.lzo.resolve() / 'liblzo2.a',
             a.compat.resolve() / 'libnextstepcompat.a']
record = {'toolchain_manifest_sha256': hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest(),
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'imports_sha256': {str(n): hashlib.sha256(n.read_bytes()).hexdigest() for n in libraries}, 'cases': {}}
flags = ['-L' + str(n) for n in [a.iconv.resolve(), a.lzo.resolve(), a.compat.resolve()]]
orders = [('dependency-first', libraries), ('newest-first', [libraries[2], *libraries[:2]]),
          ('search-dependency-first', flags + ['-liconv', '-llzo2', '-lnextstepcompat']),
          ('search-newest-first', flags + ['-lnextstepcompat', '-liconv', '-llzo2'])]
for arch in ['m68k', 'i386', 'hppa', 'sparc']:
    for name, order in orders:
        case = arch + '-' + name
        cmd = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch, '-O2', str(source),
               *map(str, order), '-o', str(out / case)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (out / (case + '.log')).write_text(r.stdout + r.stderr)
        record['cases'][case] = {'command': cmd, 'exitcode': r.returncode}
        print(case + ': ' + str(r.returncode), flush=True)
for source_path, expected in record['imports_sha256'].items():
    assert hashlib.sha256(Path(source_path).read_bytes()).hexdigest() == expected
if all(c['exitcode'] == 0 for c in record['cases'].values()):
    expected = json.loads((a.compat / 'shared-build.json').read_text())['minor_version']
    for name in record['cases']:
        raw = (out / name).read_bytes()
        endian = '<' if raw[:4] == b'\xce\xfa\xed\xfe' else '>'
        cursor = 28; identities = {}
        for _ in range(struct.unpack_from(endian + 'I', raw, 16)[0]):
            command, size = struct.unpack_from(endian + 'II', raw, cursor)
            if command == 6:
                offset, minor, address = struct.unpack_from(endian + 'III', raw, cursor + 8)
                identity = raw[cursor + offset:cursor + size].split(b'\0')[0].decode()
                assert identity not in identities
                identities[identity] = minor
            cursor += size
        assert identities['/usr/local/lib/libnextstepcompat.1.shlib'] == expected
        record['cases'][name]['load_identities'] = identities
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
assert all(c['exitcode'] == 0 for c in record['cases'].values()), 'Shared import closure is library-order dependent'
