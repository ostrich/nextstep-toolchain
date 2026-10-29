#!/usr/bin/env python3
"""Compile original SDK headers and execute libc probes on a disposable guest."""
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
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--overlay', type=Path, default=ROOT / 'work/sdk-compat')
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
args = p.parse_args()
if not args.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
GuestAgent = runpy.run_path(str(args.agent_client))['GuestAgent']
build = ROOT / 'work/build-i386/gcc'
sdk = args.sdk.resolve()
includes = sdk / 'usr/include'
out = ROOT / 'work/sdk-tests'
out.mkdir(parents=True, exist_ok=True)
compiler_id = digest(build / 'cc1')
patch_id = patch_hashes(ROOT)
records = []
with GuestAgent(str(args.socket), timeout=45) as guest:
    for standard in ['gnu89', 'gnu11', 'gnu23']:
        assembly = out / (standard + '.s')
        command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2',
                   '-std=' + standard, '-D_NEXT_SOURCE', '-nostdinc',
                   '-isystem', str(args.overlay.resolve()), '-isystem', str(build / 'include'),
                   '-idirafter', str(includes), '-idirafter', str(includes / 'ansi'),
                   '-idirafter', str(includes / 'bsd'), '-S',
                   str(ROOT / 'tests/libc-smoke.c'), '-o', str(assembly)]
        r = subprocess.run(command, capture_output=True, text=True)
        record = {'standard': standard, 'compiler_command': command,
                  'compiler_sha256': compiler_id, 'patches_sha256': patch_id,
                  'fixture_sha256': digest(ROOT / 'tests/libc-smoke.c'),
                  'compiler_status': r.returncode, 'compiler_stdout': r.stdout,
                  'compiler_stderr': r.stderr, 'steps': []}
        records.append(record)
        (out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
        if r.returncode:
            raise SystemExit(standard + ' compilation failed: ' + r.stderr)
        guest.upload(assembly, args.directory + '/libc-smoke.s')
        for label, text, expected in [
            ('assemble', '/bin/as -arch i386 libc-smoke.s -o libc-smoke.o', None),
            ('4.2 link', '/bin/cc -arch i386 libc-smoke.o -o libc42', None),
            ('4.2 execution', './libc42', 'libc smoke: passed'),
            ('3.3 SDK link', '/bin/cc -arch i386 -static -nostdlib sdk33/lib/crt0.o libc-smoke.o libcc33.a sdk33/lib/libsys_s.a -o libc33', None),
            ('3.3 SDK execution on selected guest', './libc33', 'libc smoke: passed')]:
            r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(args.directory) + ' && ' + text], execution_timeout=60)
            entry = {'name': label, 'command': text, 'exitcode': r.get('exitcode'),
                     'stdout': r['stdout'].decode('ascii', errors='replace'),
                     'stderr': r['stderr'].decode('ascii', errors='replace')}
            record['steps'].append(entry)
            (out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
            print(standard + ' ' + label + ': ' + entry['stdout'] + entry['stderr'], flush=True)
            if r.get('exitcode') != 0 or (expected and entry['stdout'].strip() != expected):
                raise SystemExit(standard + ' ' + label + ' failed')
        for binary in ['libc33', 'libc42']:
            guest.download(args.directory + '/' + binary, out / (standard + '-' + binary))
