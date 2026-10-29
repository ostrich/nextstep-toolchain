#!/usr/bin/env python3
"""Check the i386 DWARF CIE uses standard ESP numbering, not the stabs map."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['sdk', 'compiler-build', 'host-tools', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source, obj = out / 'frame.c', out / 'frame.o'
    source.write_text('int frame(int x) { volatile int local = x; return local + 1; }\n')
    command = [sys.executable, str(ROOT / 'tools/nextstep-gcc'), '--compiler-build',
               str(a.compiler_build.resolve()), '--host-tools', str(a.host_tools.resolve()),
               '--sdk', str(a.sdk.resolve()), '-arch', 'i386', '-O2', '-gdwarf-4',
               '-c', str(source), '-o', str(obj)]
    subprocess.run(command, check=True, capture_output=True)
    data = obj.read_bytes()
    magic, cpu, _, _, ncmds, cmdsize, _ = struct.unpack_from('<7I', data)
    assert magic == 0xfeedface and cpu == 7
    position, frame = 28, None
    for _ in range(ncmds):
        kind, size = struct.unpack_from('<2I', data, position)
        assert size >= 8 and position + size <= 28 + cmdsize
        if kind == 1:
            count = struct.unpack_from('<I', data, position + 48)[0]
            for index in range(count):
                section = position + 56 + index * 68
                if data[section:section + 16].rstrip(b'\0') == b'__debug_frame':
                    length, offset = struct.unpack_from('<2I', data, section + 36)
                    frame = data[offset:offset + length]
        position += size
    assert frame is not None and len(frame) >= 16
    length, marker = struct.unpack_from('<2I', frame)
    assert marker == 0xffffffff and length + 4 <= len(frame)
    assert frame[8] == 3 and frame[9] == 0, 'Expected the classic DWARF CIE version 3'
    assert frame[10:13] == bytes([1, 0x7c, 8]), 'Unexpected CIE alignment or return register'
    assert frame[13:16] == bytes([0x0c, 4, 4]), 'CFA must be ESP (DWARF register 4) + 4'
    record = {'command': command, 'object_sha256': hashlib.sha256(data).hexdigest(),
              'compiler_record_sha256': hashlib.sha256((a.compiler_build / 'build-record.json').read_bytes()).hexdigest(),
              'cie': {'stack_pointer_register': 4, 'initial_cfa_offset': 4, 'return_register': 8}, 'passed': True}
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print('i386 DWARF register numbering: PASS')


if __name__ == '__main__':
    main()
