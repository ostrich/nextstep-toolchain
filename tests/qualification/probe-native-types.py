#!/usr/bin/env python3
"""Record type evidence from a privately supplied original NeXT frontend.

For the Intel probe, supply /lib/i386/cc1obj from the original 3.3 installation.
A universal executable is thinned to its Intel host slice locally. The tool
neither reads nor changes an original disk image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shlex
import struct
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
p.add_argument('--preprocess-arch', choices=['i386', 'm68k', 'sparc'], help='override the native preprocessor architecture for this header-free probe')
p.add_argument('--frontend', type=Path, required=True)
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
args = p.parse_args()
if not args.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
type_flag = '-DEXPECT_INT_PTRDIFF' if args.arch in ['sparc', 'hppa'] else ''
out = ROOT / 'work' / ('native-types' if args.arch == 'i386' else 'native-types-' + args.arch)
out.mkdir(parents=True, exist_ok=True)
data = args.frontend.read_bytes()
source_hash = hashlib.sha256(data).hexdigest()
if data[:4] == b'\xca\xfe\xba\xbe':
    count = struct.unpack_from('>I', data, 4)[0]
    for i in range(count):
        cpu, subtype, offset, size, align = struct.unpack_from('>5I', data, 8 + 20 * i)
        if cpu == 7:
            if offset + size > len(data):
                raise SystemExit('Truncated fat slice')
            data = data[offset:offset + size]
            break
    else:
        raise SystemExit('No Intel host slice')
if len(data) < 28 or struct.unpack_from('<II', data) != (0xfeedface, 7):
    raise SystemExit('Frontend is not a 32-bit Intel Mach-O executable')
frontend = out / 'frontend'
frontend.write_bytes(data)
GuestAgent = runpy.run_path(str(args.agent_client))['GuestAgent']
with GuestAgent(str(args.socket), timeout=45) as guest:
    frontend_name = 'reference-frontend' if args.arch == 'i386' else 'reference-frontend-' + args.arch
    guest.upload(frontend, args.directory + '/' + frontend_name)
    guest.upload(ROOT / 'tests/native-types.c', args.directory + '/native-types.c')
    command = ' && '.join([
        'cd ' + shlex.quote(args.directory),
        '/bin/chmod 755 ' + frontend_name,
        '/bin/cc -arch ' + (args.preprocess_arch or args.arch)
        + ' -static -traditional-cpp -E ' + type_flag
        + ' native-types.c -o native-types.i',
        './' + frontend_name + ' -version -quiet -O2 native-types.i -o native-types.s'])
    r = guest.execute('/bin/sh', ['-c', command], execution_timeout=60)
    record = {'target_arch': args.arch, 'preprocess_arch': args.preprocess_arch or args.arch,
              'fixture_sha256': hashlib.sha256((ROOT / 'tests/native-types.c').read_bytes()).hexdigest(),
              'source_frontend_sha256': source_hash,
              'intel_frontend_sha256': hashlib.sha256(data).hexdigest(),
              'command': command, 'exitcode': r.get('exitcode'),
              'stdout': r['stdout'].decode('ascii', errors='replace'),
              'stderr': r['stderr'].decode('ascii', errors='replace')}
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print(record['stdout'] + record['stderr'])
    if r.get('exitcode') != 0:
        raise SystemExit('Original frontend type probe failed')
    guest.download(args.directory + '/native-types.s', out / 'native-types.s')
print((out / 'native-types.s').read_text())
