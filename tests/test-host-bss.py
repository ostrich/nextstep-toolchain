#!/usr/bin/env python3
"""Check classic assembler BSS layout when .zerofill precedes .lcomm."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tools', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
tools, output = a.tools.resolve(), a.output.resolve()
output.mkdir(parents=True, exist_ok=True)
source = output / 'mixed-bss.s'
source.write_text('''.text
.long 0
.globl _before
.zerofill __DATA,__bss,_before,4,2
.lcomm _local,8,3
.globl _after
.zerofill __DATA,__bss,_after,4,2
''')

def inspect(path):
    data = path.read_bytes()
    endian = '>' if data[:4] == b'\xfe\xed\xfa\xce' else '<'
    header = struct.unpack_from(endian + '7I', data)
    if header[0] != 0xfeedface:
        raise ValueError('Expected 32-bit Mach-O')
    offset = 28
    sections = []
    for _ in range(header[4]):
        command, size = struct.unpack_from(endian + '2I', data, offset)
        if command == 1:
            count = struct.unpack_from(endian + 'I', data, offset + 48)[0]
            for index in range(count):
                section = struct.unpack_from(endian + '16s16s9I', data, offset + 56 + index * 68)
                sections.append(section)
        elif command == 2:
            _, _, symbols, symbol_count, strings, _ = struct.unpack_from(endian + '6I', data, offset)
        offset += size
    found = {}
    for index in range(symbol_count):
        name, kind, section, _, value = struct.unpack_from(endian + 'IBBHI', data, symbols + index * 12)
        name = data[strings + name:].split(b'\0', 1)[0].decode()
        if name not in ('_before', '_local', '_after'):
            continue
        sect = sections[section - 1]
        if kind & 0x0e != 0x0e or sect[0].rstrip(b'\0') != b'__bss':
            raise ValueError('Wrong symbol section: ' + name)
        relative = value - sect[2]
        expected = {'_before': 0, '_local': 8, '_after': 16}[name]
        if relative != expected or sect[3] != 20:
            raise ValueError(f'{name}: offset {relative}, section size {sect[3]}; expected {expected}, 20')
        found[name] = relative
    if len(found) != 3:
        raise ValueError('Missing test symbols')
    return found

results = []
for arch in ('i386', 'm68k', 'sparc', 'hppa'):
    obj = output / (arch + '.o')
    subprocess.run([str(tools / ('as-' + arch)), '-o', str(obj), str(source)], check=True)
    results.append({'arch': arch, 'symbols': inspect(obj)})
(output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print('Mixed .zerofill/.lcomm layout passed on all four architectures.')
