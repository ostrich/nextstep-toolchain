#!/usr/bin/env python3
"""Compare classic Mach-O output across host ABIs using qualified reference tools."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tools', type=Path, required=True)
references = p.add_mutually_exclusive_group(required=True)
references.add_argument('--reference', type=Path)
references.add_argument('--reference-output', type=Path, help='Retained reference outputs from another host')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, ZERO_AR_DATE='1')
results = []
for arch in ['i386', 'm68k', 'sparc', 'hppa']:
    d = out / arch
    d.mkdir(exist_ok=True)
    # Adjacent bytes catch an eight-byte store where a relocation is four bytes.
    source = d / 'words.s'
    source.write_text('.data\n.globl _word, _destination\n_word:\n'
                      '.long _destination\n.byte 17,34,51,68\n'
                      '_destination:\n.long 0x12345678\n'
                      '.comm _common,16\n.non_lazy_symbol_pointer\n'
                      'L_indirect_pointer:\n'
                      '.indirect_symbol _destination\n.long 0\n'
                      '.literal4\n.long 0x11223344,0x55667788\n'
                      '.literal8\n.long 0x12345678,0x90abcdef\n'
                      '.long 0x13579bdf,0x2468ace0\n')
    refsource = d / 'reference.s'
    refsource.write_text('.data\n.globl _reference\n_reference:\n.long _word\n')
    if a.reference_output:
        for suffix in ['-words.o', '-reference.o', '-linked.o']:
            shutil.copy2(a.reference_output / arch / ('reference' + suffix), d / ('reference' + suffix))
    runs = [('candidate', a.tools.resolve())]
    if a.reference:
        runs.insert(0, ('reference', a.reference.resolve()))
    for tag, tools in runs:
        first, second = d / (tag + '-words.o'), d / (tag + '-reference.o')
        archive, linked = d / (tag + '.a'), d / (tag + '-linked.o')
        archive.unlink(missing_ok=True)
        commands = [
            [tools / ('as-' + arch), '-o', first, source],
            [tools / ('as-' + arch), '-o', second, refsource],
            [tools / 'ar', 'rcs', archive, first],
            [tools / 'ld', '-arch', arch, '-r', '-o', linked, second, archive],
        ]
        for i, cmd in enumerate(commands):
            r = subprocess.run(list(map(str, cmd)), env=env, capture_output=True)
            (d / (tag + '-' + str(i) + '.log')).write_bytes(r.stdout + r.stderr)
            if r.returncode:
                raise SystemExit(f'{arch}: {tag} command {i} failed')
    for suffix in ['-words.o', '-reference.o', '-linked.o']:
        if (d / ('reference' + suffix)).read_bytes() != (d / ('candidate' + suffix)).read_bytes():
            raise SystemExit(f'{arch}: output differs for {suffix}')
    results.append({'target': arch, 'object_and_linked_bytes_equal': True})
(out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print('PASS: four-target objects and selective archive links match reference bytes')
