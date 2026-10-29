#!/usr/bin/env python3
"""Build the pinned FlatBuffers compiler with recorded target adaptations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--jobs', type=int, default=4)
a = p.parse_args()
if a.jobs < 1:
    p.error('--jobs must be positive')
pin = json.loads((ROOT / 'tests/cxx-runtime/flatbuffers-source.json').read_text())
archive = ROOT / ('work/downloads/flatbuffers-' + pin['version'] + '.tar.gz')
if not archive.exists():
    urllib.request.urlretrieve(pin['url'], archive)
if hashlib.sha256(archive.read_bytes()).hexdigest() != pin['sha256']:
    raise SystemExit('FlatBuffers release hash mismatch')
src = ROOT / ('work/app-sources/flatbuffers-' + pin['version'].removeprefix('v'))
if not src.exists():
    with tarfile.open(archive) as t:
        t.extractall(src.parent, filter='data')
with tarfile.open(archive) as t:
    for member in t:
        if member.isfile():
            path = src.parent / member.name
            if not path.is_file() or path.read_bytes() != t.extractfile(member).read():
                raise SystemExit('Modified upstream source: ' + str(path))
text = (src / 'CMakeLists.txt').read_text()
names = []
for variable in ['FlatBuffers_Library_SRCS', 'FlatBuffers_Compiler_SRCS']:
    block = re.search(r'set\(' + variable + r'\s+(.*?)\n\)', text, re.S)
    if not block:
        raise SystemExit('Cannot find upstream source list: ' + variable)
    for name in re.findall(r'\b[\w/]+\.(?:cpp|cc)\b', block.group(1)):
        if name not in names:
            names.append(name)
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
prepared = out / 'source'
if prepared.exists():
    shutil.rmtree(prepared)
shutil.copytree(src, prepared)
patches = sorted((ROOT / 'tests/cxx-runtime/flatbuffers').glob('*.patch'))
for patch in patches:
    subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch)],
                   cwd=prepared, check=True)
src = prepared
common = [str(a.toolchain.resolve() / 'bin/nextstep-g++'), '--sdk', str(a.sdk.resolve()),
          '-arch', a.arch, '-O2', '-std=gnu++17', '-I' + str(src / 'include'),
          '-I' + str(src / 'grpc'), '-DFLATBUFFERS_LOCALE_INDEPENDENT=0']
def compile_one(name):
    obj = out / (name.replace('/', '_') + '.o')
    command = common + ['-c', str(src / name), '-o', str(obj),
                        '--build-record', str(obj.with_suffix('.json'))]
    with obj.with_suffix('.log').open('wb') as log:
        r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError('Compilation failed: ' + str(obj.with_suffix('.log')))
    return obj
with ThreadPoolExecutor(max_workers=a.jobs) as pool:
    objects = list(pool.map(compile_one, names))
command = common + [str(o) for o in objects] + ['-o', str(out / 'flatc'),
           '--build-record', str(out / 'link.json')]
with (out / 'link.log').open('wb') as log:
    r = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
if r.returncode:
    raise SystemExit('Link failed: ' + str(out / 'link.log'))
(out / 'application.json').write_text(json.dumps({'upstream': pin, 'arch': a.arch,
    'patches_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in patches},
    'source_files': names, 'optimization': '-O2',
    'executable_sha256': hashlib.sha256((out / 'flatc').read_bytes()).hexdigest(),
    'execution_status': 'not tested'}, indent=2) + '\n')
print('Built full upstream flatc from ' + str(len(names)) + ' C++ units; guest execution required.')
