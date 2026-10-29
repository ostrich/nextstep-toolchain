#!/usr/bin/env python3
"""Check recorded four-target runtime closure against its exact build inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--inputs', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
spec = json.loads(a.inputs.read_text())
def path(name):
    return (ROOT / name).resolve()
def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()
def require(value, message):
    if not value:
        raise SystemExit(message)

bundle = path(spec['toolchain'])
manifest = json.loads((bundle / 'toolchain.json').read_text())
for name, expected in manifest['files'].items():
    file = bundle / name
    require(file.resolve().is_relative_to(bundle), 'Bundle path escapes: ' + name)
    require(digest(file) == expected, 'Bundle mismatch: ' + name)
for name, expected in manifest['gcc_patches_sha256'].items():
    require(digest(ROOT / 'patches' / name) == expected, 'Patch snapshot mismatch: ' + name)
baseline = json.loads((ROOT / 'work/cxx-runtime/baseline.json').read_text())['gcc_patches']
require(all(manifest['gcc_patches_sha256'][n] == h for n, h in baseline.items()),
        'Frozen predecessor patches changed')
replay = json.loads(path(spec['source_audit']).read_text())
require(replay['full_source_verification'], 'Complete upstream source audit missing')
require(replay['patches_sha256'] == manifest['gcc_patches_sha256'], 'Source audit snapshot mismatch')
fixtures = path(spec['fixtures'])
host = json.loads((fixtures / 'host-results.json').read_text())
require(host and all(r.get('exitcode', 0) == 0 and r.get('passed', True) for r in host),
        'Installed-driver host regression failure')
guest_hashes = json.loads((fixtures / 'guest-inputs.json').read_text())
names = set(guest_hashes['i386']) - {'runtime-batch'}
require(len(names) == 13, 'Expected all 13 runtime/application programs')
records = {}
for arch, info in spec['guests'].items():
    logpath = path(info['log'])
    text = logpath.read_text()
    if arch in ('sparc', 'hppa'):
        exits = re.findall(r'^BATCH EXIT ([\w-]+) (-?\d+)$', text, re.M)
        require('runtime batch: 13 programs, 0 failures' in text, arch + ' batch incomplete')
    elif arch == 'm68k':
        exits = re.findall(r'^EXIT ([\w-]+) (-?\d+)$', text, re.M)
        require('CXX RUNTIME END' in text, 'm68k batch incomplete')
    else:
        exits = re.findall(r'^RUN:([\w-]+)\n.*?^EXIT:(-?\d+)$', text, re.M | re.S)
    require(len(exits) == 13 and {n for n, _ in exits} == names
            and all(status == '0' for _, status in exits), arch + ' program exits incomplete or failing')
    require(not re.search(r'^FAIL|\b[1-9][0-9]* failures\b', text, re.M), arch + ' explicit test failure')
    for expected in ['800 exceptions, 5 TLS destructors, 0 failures',
                     'floating conversion: 67 checks, 0 failures',
                     'floating immediates: 66 checks, 0 failures',
                     'C99 C++: 18 checks, 0 failures',
                     'flatc application: 5 generation cases, 0 failures',
                     're2c application: 7 generation cases, 0 failures']:
        require(expected in text, arch + ': missing ' + expected)
    if arch == 'openstep42':
        staged = json.loads(path(info['staged_inputs']).read_text())['probes']
        for name in names:
            require(staged.get(name) == guest_hashes['i386'][name], 'OPENSTEP stale fixture: ' + name)
        for app in ('flatc', 're2c'):
            require(staged.get(app) == digest(path(spec['applications']['i386'][app]) / app),
                    'OPENSTEP stale application: ' + app)
    else:
        staged = json.loads(path(info['staged_inputs']).read_text())
        if arch in ('sparc', 'hppa'):
            staged = staged[arch]
        elif arch == 'm68k':
            staged = {**staged['probes'], **staged['assets']}
        else:
            staged = staged['probes']
        for name in names:
            require(staged.get(name) == guest_hashes[arch][name], arch + ' stale staged fixture: ' + name)
        for app in ('flatc', 're2c'):
            build = path(spec['applications'][arch][app])
            require(staged.get(app) == digest(build / app), arch + ' stale staged ' + app)
            apprecord = json.loads((build / 'application.json').read_text())
            require(apprecord['optimization'] == '-O2' and apprecord['executable_sha256'] == staged[app],
                    arch + ' application build record mismatch')
        fsck = path(info['fsck']).read_text()
        require('Phase 5' in fsck and not re.search(r'\b(?:BAD|UNREF|INCORRECT|SALVAGE)\b', fsck),
                arch + ' filesystem evidence missing or failing')
        require(path(info['halt_evidence']).is_file(), arch + ' native halt evidence missing')
    records[arch] = {'programs': 13, 'failures': 0, 'log': str(logpath.relative_to(ROOT.parent)),
                     'log_sha256': digest(logpath)}
require(set(records) == {'i386', 'm68k', 'sparc', 'hppa', 'openstep42'}, 'Target/compatibility coverage missing')
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps({'toolchain': spec['toolchain'], 'gcc_patches_sha256': manifest['gcc_patches_sha256'],
    'full_source_files': replay['untouched_upstream_files'] + len(replay['source_sha256']),
    'guests': records, 'status': 'passed'}, indent=2) + '\n')
print('Four-target runtime/application closure and OPENSTEP compatibility evidence pass.')
