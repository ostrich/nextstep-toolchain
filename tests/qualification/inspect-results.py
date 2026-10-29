#!/usr/bin/env python3
"""Audit the old Mach-O load commands that modern llvm-objdump rejects."""
import argparse
import json
from pathlib import Path
import struct
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path)
parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
args = parser.parse_args()
root = args.root or ROOT / 'work' / ('abi' if args.arch == 'i386' else 'abi-' + args.arch)
endian = '<' if args.arch == 'i386' else '>'
cpu = {'i386': 7, 'm68k': 6, 'sparc': 14, 'hppa': 11}[args.arch]
results = {}
for opt in ['O1', 'O2', 'O3', 'Os']:
    results[opt] = {}
    for name in (['mixed33', 'mixed42'] if args.arch == 'i386' else ['mixed33']):
        data = (root / opt / name).read_bytes()
        head = struct.unpack_from(endian + '7I', data)
        if head[0] != 0xfeedface or head[1] != cpu:
            raise SystemExit(f'{opt}/{name}: not the expected 32-bit Mach-O architecture')
        offset = 28
        commands = []
        for _ in range(head[4]):
            cmd, size = struct.unpack_from(endian + 'II', data, offset)
            if size < 8 or offset + size > 28 + head[5]:
                raise SystemExit('Invalid load command size')
            entry = {'command': cmd, 'size': size}
            if cmd in [6, 12, 13, 14, 15]:
                name_offset = struct.unpack_from(endian + 'I', data, offset + 8)[0]
                if not 12 <= name_offset < size:
                    raise SystemExit('Invalid load command name offset')
                entry['name'] = data[offset + name_offset:offset + size].split(b'\0', 1)[0].decode('ascii')
            commands.append(entry)
            offset += size
        if offset != 28 + head[5]:
            raise SystemExit('Load commands do not fill their declared extent')
        if name == 'mixed33':
            valid = any(c['command'] == 6 and c.get('name') == '/usr/shlib/libsys_s.B.shlib' for c in commands)
        else:
            valid = any('System.framework' in c.get('name', '') for c in commands)
        if not valid:
            raise SystemExit(f'{opt}/{name}: unexpected runtime linkage')
        results[opt][name] = {'cpu': args.arch, 'commands': commands}
(root / 'load-commands.json').write_text(json.dumps(results, indent=2) + '\n')
print(args.arch + ': all Mach-O executables have the expected architecture and runtime linkage.')
