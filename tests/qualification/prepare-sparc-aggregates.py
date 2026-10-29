#!/usr/bin/env python3
"""Link native/modern SPARC aggregate boundary probes for NS3.3 execution."""
import argparse
import json
from pathlib import Path
import sys
import runpy
import shlex
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
p.add_argument('--native-frontend', default='./reference-frontend-sparc')
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
a = p.parse_args()
if not a.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
out = ROOT / 'work/sparc-small-aggregates'
out.mkdir(exist_ok=True)
build = ROOT / 'work/build-sparc/gcc'
source = ROOT / 'tests/sparc-small-aggregates.c'
record = {'execution_performed': False, 'source_sha256': digest(source),
          'patches_sha256': patch_hashes(ROOT), 'compiler_sha256': digest(build / 'cc1'),
          'native_frontend': a.native_frontend, 'steps': []}
def save():
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
for name, flags in [('modern-functions', ['-DPREFIX=modern_']), ('modern-main', [])]:
    cmd = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2', *flags,
           '-S', str(source), '-o', str(out / (name + '.s'))]
    r = subprocess.run(cmd, capture_output=True, text=True)
    record['steps'].append({'command': cmd, 'exitcode': r.returncode,
                            'stdout': r.stdout, 'stderr': r.stderr})
    save()
    if r.returncode:
        raise SystemExit(r.stderr)
Agent = runpy.run_path(str(a.agent_client))['GuestAgent']
with Agent(str(a.socket), timeout=45) as guest:
    def run(cmd):
        r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(a.directory) + ' && ' + cmd], execution_timeout=90)
        record['steps'].append({'command': cmd, 'exitcode': r.get('exitcode'),
                                'stdout': r['stdout'].decode(errors='replace'),
                                'stderr': r['stderr'].decode(errors='replace')})
        save()
        if r.get('exitcode') != 0:
            raise SystemExit(str(record['steps'][-1]))
    guest.upload(source, a.directory + '/sparc-small-aggregates.c')
    for name, flags in [('native-functions', '-DPREFIX=native_'), ('native-main', '')]:
        run('/bin/cc -arch sparc -static -traditional-cpp -E ' + flags +
            ' sparc-small-aggregates.c -o ssa-' + name + '.i && ' +
            shlex.quote(a.native_frontend) + ' -quiet -O2 ssa-' + name +
            '.i -o ssa-' + name + '.s')
        guest.download(a.directory + '/ssa-' + name + '.s', out / (name + '.s'))
    for name in ['modern-functions', 'modern-main']:
        guest.upload(out / (name + '.s'), a.directory + '/ssa-' + name + '.s')
    for name in ['native-functions', 'modern-functions', 'native-main', 'modern-main']:
        run('/bin/as -arch sparc ssa-' + name + '.s -o ssa-' + name + '.o')
    for main in ['native-main', 'modern-main']:
        binary = main + '33'
        run('/bin/cc -arch sparc -static -nostdlib sdk33/lib/crt0.o ssa-' +
            main + '.o ssa-native-functions.o ssa-modern-functions.o ' +
            'sdk33/lib/sparc/libcc.a sdk33/lib/libsys_s.a -o ssa-' + binary)
        guest.download(a.directory + '/ssa-' + binary, out / binary)
        record.setdefault('executables_sha256', {})[binary] = digest(out / binary)
        save()
print('Prepared two 18-check executables; target execution remains required.')
