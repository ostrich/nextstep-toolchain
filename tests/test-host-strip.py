#!/usr/bin/env python3
"""Check that classic strip preserves executable code, data and ABI load commands."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
tc = a.toolchain.resolve(strict=True)
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
source = out / 'fixture.c'
source.write_text('const char message[]="strip fixture"; int main(void){return message[0]!=115;}\n')
def executable(path):
    b = path.read_bytes()
    endian = '>' if b[:4] == b'\xfe\xed\xfa\xce' else '<'
    header = struct.unpack_from(endian+'7I', b)
    assert header[0] == 0xfeedface and header[3] == 2
    pos = 28
    segments, abi = [], []
    for unused in range(header[4]):
        command, size = struct.unpack_from(endian+'2I', b, pos)
        assert size >= 8 and pos + size <= len(b)
        if command == 1:
            name = b[pos+8:pos+24].split(b'\0')[0]
            vmaddr, vmsize, offset, length = struct.unpack_from(endian+'4I', b, pos+24)
            if name != b'__LINKEDIT':
                # The first segment includes the intentionally rewritten load
                # commands. Everything after that header must stay identical.
                start = max(offset, 28+header[5])
                segments.append((name, vmaddr, vmsize, start, b[start:offset+length]))
        if command in (4, 5, 6, 7):
            abi.append(b[pos:pos+size])
        pos += size
    return header[1:4], segments, abi
records = []
for arch in ['i386','m68k','hppa','sparc']:
    original = out / arch
    stripped = out / (arch+'-stripped')
    subprocess.run([str(tc/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve()),'-arch',arch,
                    '-O2','-g',str(source),'-o',str(original)],check=True)
    subprocess.run([str(tc/'libexec/cctools/strip'),'-o',str(stripped),str(original)],check=True)
    assert executable(original) == executable(stripped), arch
    assert stripped.stat().st_size < original.stat().st_size, arch
    b = original.read_bytes()
    endian = '>' if b[:4] == b'\xfe\xed\xfa\xce' else '<'
    pos = 28
    padding = 0
    for unused in range(struct.unpack_from(endian+'7I', b)[4]):
        command, size = struct.unpack_from(endian+'2I', b, pos)
        if command == 2:
            unused_sym, unused_count, offset, length = struct.unpack_from(endian+'4I', b, pos+8)
            padding = len(b) - offset - length
        pos += size
    if padding > 8:
        corrupt = out / (arch+'-nonzero-tail')
        corrupt.write_bytes(b[:-1] + b'\x01')
        result = subprocess.run([str(tc/'libexec/cctools/strip'), '-o',
                                 str(out/(arch+'-must-reject')), str(corrupt)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and b'string table not at the end' in result.stderr, arch
    records.append({'architecture':arch,'before':original.stat().st_size,
                    'after':stripped.stat().st_size,'padding':padding})
assert any(r['padding'] > 8 for r in records), 'Fixture did not exercise legacy padding'
# Debug-bearing archive members take strip's relocatable-link path. Native
# NEXTSTEP/OPENSTEP archive tools reject modern LC_UUID commands in objects.
for arch in [r['architecture'] for r in records]:
    obj = out / (arch+'-dwarf.o')
    plain = out / (arch+'-nodebug.o')
    subprocess.run([str(tc/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve()),'-arch',arch,
                    '-O2','-gdwarf-4','-c',str(source),'-o',str(obj)],check=True)
    subprocess.run([str(tc/'libexec/cctools/strip'),'-S','-o',str(plain),str(obj)],check=True)
    b = plain.read_bytes()
    endian = '>' if b[:4] == b'\xfe\xed\xfa\xce' else '<'
    header = struct.unpack_from(endian+'7I', b)
    assert header[3] == 1, arch
    pos = 28
    for unused in range(header[4]):
        command, size = struct.unpack_from(endian+'2I', b, pos)
        assert command != 0x1b, 'Relocatable debug strip added LC_UUID: '+arch
        pos += size
    subprocess.run([str(tc/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve()),'-arch',arch,
                    str(plain),'-o',str(out/(arch+'-nodebug-linked'))],check=True)

fat = out/'fat'
subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*[str(out/r['architecture']) for r in records],'-output',str(fat)],check=True)
subprocess.run([str(tc/'libexec/cctools/strip'),'-o',str(out/'fat-stripped'),str(fat)],check=True)
for arch in [r['architecture'] for r in records]:
    extracted=out/(arch+'-from-fat')
    subprocess.run([str(tc/'libexec/cctools/lipo'),str(out/'fat-stripped'),'-thin',arch,'-output',str(extracted)],check=True)
    assert executable(out/arch) == executable(extracted), arch
(out/'results.json').write_text(json.dumps({'passed':True,'targets':records},indent=2)+'\n')
print('PASS strip: NIHS code/data, thread state, fixed-VM imports and fat slices preserved')
