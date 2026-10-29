#!/usr/bin/env python3
"""Check pinned libc algorithms with host sanitizers in a private namespace."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--sanitize', action='store_true')
a = p.parse_args()
out = a.output.resolve()
if out.exists():
    p.error('Use a new output directory')
out.mkdir(parents=True)
commands = []


def run(cmd, log):
    commands.append(list(map(str, cmd)))
    r = subprocess.run(commands[-1], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=90)
    log.write_bytes(r.stdout)
    if r.returncode:
        raise SystemExit('Failed; inspect ' + str(log))


for part in ['format', 'scan', 'string']:
    dest = out / part
    dest.mkdir()
    pin = json.loads((ROOT / part / 'sources.json').read_text())
    files = pin.get('files_sha256', {'vfprintf.c': pin.get('source_sha256')})
    for name, expected in files.items():
        if hashlib.sha256((ROOT / part / name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Upstream hash mismatch: ' + part + '/' + name)
        shutil.copyfile(ROOT / part / name, dest / name)
    if part == 'format':
        patches = ['0001-nextstep-bounded-output.patch', '0002-nextstep-stream-output.patch']
    elif part == 'scan':
        for name in ['scan-support.h', 'stream.c']:
            shutil.copyfile(ROOT / part / name, dest / name)
        shutil.copyfile(ROOT / 'parse/binary-scale.h', dest / 'binary-scale.h')
        patches = ['0001-nextstep-native-streams.patch']
    else:
        patches = []
    for patch in patches:
        run(['patch', '-d', dest, '-p1', '--batch', '--fuzz=0', '-i', ROOT / part / patch],
            out / (patch + '.log'))
flags = ['cc', '-O2', '-std=gnu17', '-fno-builtin']
if a.sanitize:
    flags += ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
names = ['strstr', 'strtol', 'strtoul', 'strtoll', 'strtoull', 'atoll', 'llabs', 'lldiv',
         'snprintf', 'vsnprintf', 'printf', 'vprintf', 'fprintf', 'vfprintf',
         'sscanf', 'vsscanf', 'fscanf', 'vfscanf', 'scanf', 'vscanf']
flags += ['-D' + name + '=ns33_' + name for name in names]
flags += ['-D_Exit=ns33__Exit']
(out / 'host-stream.c').write_text('#include <stdio.h>\nsize_t ns33_stream_write(FILE *f, const char *s, size_t n) { return fwrite(s,1,n,f); }\n')
objects = []
sources = sorted((out / 'scan').glob('*.c')) + [out / 'format/vfprintf.c',
          out / 'string/strstr.c', ROOT / 'src/integer-conversion.c', out / 'host-stream.c']
for i, source in enumerate(sources):
    obj = out / (str(i) + '.o')
    run([*flags, '-c', source, '-o', obj], out / (str(i) + '-build.log'))
    objects.append(obj)
cases = ['string_strstr', 'strtol', 'sscanf', 'ungetc', 'snprintf']
for name in cases:
    source = ROOT / 'tests/coverage/upstream/src/functional' / (name + '.c')
    binary = out / name
    run([*flags, '-I', ROOT / 'tests/coverage/upstream/src/common', source,
         ROOT / 'tests/coverage/harness.c', *objects, '-lm', '-o', binary],
        out / (name + '-build.log'))
    run([binary], out / (name + '.log'))
    print('Passed host algorithm check:', name, flush=True)
(out / 'results.json').write_text(json.dumps({
    'status': 'passed', 'programs': cases, 'sanitize': a.sanitize,
    'note': 'Host FILE layout differs. Native NeXT pushback adapter requires guest tests.',
    'commands': commands,
    'prepared_sha256': {str(s.relative_to(out)): hashlib.sha256(s.read_bytes()).hexdigest()
                       for s in sources if out in s.parents}}, indent=2) + '\n')
