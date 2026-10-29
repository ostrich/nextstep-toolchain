#!/usr/bin/env python3
"""Check BSD Mach-O archive creation, indexing, extraction and linkage."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tools', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
tools, output = a.tools.resolve(), a.output.resolve()
output.mkdir(parents=True, exist_ok=True)
rows = []
environment = dict(os.environ, ZERO_AR_DATE='1')
for arch in ['i386', 'm68k', 'sparc', 'hppa']:
    directory = output / arch
    directory.mkdir(exist_ok=True)
    extracted = directory / 'extracted'
    extracted.mkdir(exist_ok=True)
    assembly = directory / 'member.s'
    assembly.write_text('.data\n.globl _archive_probe\n_archive_probe:\n.long 42\n')
    member = directory / ('a-long-archive-member-name-' + arch + '.o')
    archive = directory / 'test.a'
    archive.unlink(missing_ok=True)
    commands = [[str(tools / ('as-' + arch)), '-o', str(member), str(assembly)],
                [str(tools / 'ar'), 'rcs', str(archive), str(member)],
                [str(tools / 'ar'), 'x', str(archive)],
                [str(tools / 'ld'), '-arch', arch, '-r', '-all_load',
                 str(archive), '-o', str(directory / 'linked.o')]]
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=extracted if index == 2 else directory,
                                env=environment, capture_output=True)
        (directory / ('step-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit(arch + ': failed ' + str(command))
    before, after = member.read_bytes(), (extracted / member.name).read_bytes()
    padding = after[len(before):]
    # Apple ranlib aligns members to eight bytes and may append newlines inside
    # the member's recorded size. Require the original payload unchanged.
    if not after.startswith(before) or len(padding) >= 8 or any(x != 10 for x in padding):
        raise SystemExit(arch + ': member payload changed')
    symbols = subprocess.check_output([str(tools / 'nm'), str(directory / 'linked.o')], text=True)
    if '_archive_probe' not in symbols:
        raise SystemExit(arch + ': indexed member was not linked')
    rows.append({'arch': arch, 'payload_preserved': True, 'indexed_member_linked': True,
                 'alignment_bytes': len(padding), 'archive_sha256': digest(archive),
                 'commands': commands})
(output / 'results.json').write_text(json.dumps({
    'tools_sha256': {name: digest(tools / name) for name in ['ar', 'ranlib', 'ld']},
    'architectures': rows}, indent=2) + '\n')
print('Four architectures: archive payload, long filename, index and link checks passed.')
