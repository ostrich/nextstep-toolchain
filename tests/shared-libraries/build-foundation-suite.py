#!/usr/bin/env python3
"""Assemble one hashed NIHS shared-foundation batch for disposable guests."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ['compat-tests', 'threads', 'network', 'mock-network', 'data', 'dependencies', 'shared', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
compat = json.loads((a.compat_tests / 'build-record.json').read_text())['artifacts']
assets = {name: (a.compat_tests / name).resolve() for name in compat}
assets.update({'threads': a.threads.resolve() / 'threads',
               'network': a.network.resolve() / 'network',
               'network-mock': a.mock_network.resolve() / 'network-mock',
               'data-consumer': a.data.resolve() / 'consumer',
               'data-upgrade.shlib': a.data.resolve() / '2/libdatatest.1.shlib'})
for name in ['consumer', 'require2', 'leaf-upgrade.shlib', 'run-dependencies.sh']:
    assets[name] = a.dependencies.resolve() / name
libraries = {'libnextstepcompat.1.shlib': a.shared.resolve() / 'libnextstepcompat.1.shlib',
             'libdatatest.1.shlib': a.data.resolve() / '1/libdatatest.1.shlib'}
for name in ['leaf', 'left', 'right', 'top']:
    filename = 'libdep' + name + '.1.shlib'
    libraries[filename] = a.dependencies.resolve() / filename
probes = [*compat, 'threads', 'network', 'network-mock']
# The existing four-guest bootstrap expects this filename; the assertions
# below concern the shared foundation, not codec coverage.
runner = out / 'run-codecs.sh'
runner.write_text('''#!/bin/sh
cd "$1" || exit 90
status=0
for probe in PROBES; do
 echo "RUN $probe"
 ./$probe "$1"
 result=$?
 echo "EXIT $probe $result"
 test "$result" = 0 || status=1
done
library=/usr/local/lib/libdatatest.1.shlib
cp "$library" data-original.shlib || exit 91
./data-consumer || status=1
cp data-upgrade.shlib "$library" || exit 92
chmod 755 "$library" || exit 93
./data-consumer || status=1
cp data-original.shlib "$library" || exit 94
chmod 755 "$library" || exit 95
/bin/sh ./run-dependencies.sh "$1" || status=1
test "$status" = 0 || exit 1
echo 'PASS canonical shared foundation batch complete'
'''.replace('PROBES', ' '.join(probes)))
runner.chmod(0o755)
assets['run-codecs.sh'] = runner
inputs = {'libraries': {n: str(path) for n, path in libraries.items()},
          'assets': {n: str(path) for n, path in assets.items()},
          'sha256': {n: digest(path) for n, path in {**libraries, **assets}.items()},
          'coverage': 'shared compatibility, threading, networking, terminal, data/function identity and dependency upgrades'}
(out / 'suite.json').write_text(json.dumps(inputs, indent=2) + '\n')
print('Prepared hashed shared-foundation suite')
