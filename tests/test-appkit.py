#!/usr/bin/env python3
"""Build a small original-AppKit application against the private 3.3 SDK.

Intel output executes in the selected build guest; other output is prepared for
separate execution. The app creates a native window/control and exits on a timer.
"""
import argparse
import json
from pathlib import Path
import sys
import runpy
import shlex
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k'], default='i386')
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--kit-library', type=Path, required=True, help='private original libNeXT_s.a')
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
args = p.parse_args()
if not args.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
build = ROOT / 'work' / ('build-' + args.arch) / 'gcc'
out = ROOT / 'work' / ('appkit-' + args.arch)
out.mkdir(exist_ok=True)
headers = args.sdk.resolve() / 'usr/include'
command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2', '-std=gnu89', '-nostdinc',
           '-isystem', str(ROOT / 'work/sdk-compat'), '-isystem', str(build / 'include'),
           '-idirafter', str(headers), '-idirafter', str(headers / 'ansi'),
           '-idirafter', str(headers / 'bsd'), '-S', str(ROOT / 'tests/appkit-smoke.m'),
           '-o', str(out / 'appkit.s')]
r = subprocess.run(command, capture_output=True, text=True)
record = {'arch': args.arch, 'patches_sha256': patch_hashes(ROOT),
          'compiler_sha256': digest(build / 'cc1obj'),
          'fixture_sha256': digest(ROOT / 'tests/appkit-smoke.m'),
          'kit_library_sha256': digest(args.kit_library),
          'compilation': {'command': command, 'exitcode': r.returncode, 'stderr': r.stderr},
          'steps': []}
def save():
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
save()
if r.returncode:
    raise SystemExit(r.stderr)
GuestAgent = runpy.run_path(str(args.agent_client))['GuestAgent']
with GuestAgent(str(args.socket), timeout=45) as guest:
    def run(name, command, expected=None):
        r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(args.directory) + ' && ' + command], execution_timeout=60)
        row = {'name': name, 'command': command, 'exitcode': r.get('exitcode'),
               'stdout': r['stdout'].decode('ascii', errors='replace'),
               'stderr': r['stderr'].decode('ascii', errors='replace')}
        record['steps'].append(row)
        save()
        print(name + ': ' + row['stdout'] + row['stderr'], flush=True)
        if r.get('exitcode') != 0 or (expected and expected not in row['stdout']):
            raise SystemExit(name + ' failed')
    guest.upload(out / 'appkit.s', args.directory + '/appkit.s')
    guest.upload(args.kit_library, args.directory + '/libNeXT33.a')
    run('assembly', '/bin/as -arch ' + args.arch + ' appkit.s -o appkit.o')
    run('copied archive index', '/bin/ranlib libNeXT33.a')
    support = 'libcc33.a' if args.arch == 'i386' else 'sdk33/lib/' + args.arch + '/libcc.a'
    run('3.3 SDK link', '/bin/cc -arch ' + args.arch + ' -static -nostdlib sdk33/lib/crt0.o appkit.o ' + support + ' libNeXT33.a sdk33/lib/libsys_s.a -o appkit33')
    guest.download(args.directory + '/appkit33', out / 'appkit33')
    if args.arch == 'i386':
        run('execution', './appkit33', 'appkit probe: passed')
print('AppKit probe complete; see results for assembly/link and execution coverage.')
