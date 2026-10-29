#!/usr/bin/env python3
"""Prepare optimized cross-target mixed-compiler executables for a separate 3.3 guest.

The selected Intel build guest supplies original cross assembler/linker tools.
This script assembles and links; it does not claim target execution.
"""
import argparse
import json
from pathlib import Path
import sys
import runpy
import shlex
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--arch', choices=['m68k', 'sparc', 'hppa'], required=True)
p.add_argument('--native-frontend')
p.add_argument('--reference-only', action='store_true',
               help='Use only original-compiler objects and original runtime helpers')
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
p.add_argument('--optimization', choices=['O1', 'O2', 'O3', 'Os'], default='O2')
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
args = p.parse_args()
if not args.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
if args.native_frontend is None:
    args.native_frontend = args.directory + '/reference-frontend-' + args.arch
build = ROOT / 'work' / ('build-' + args.arch) / 'gcc'
source = ROOT / 'work/gcc-16.2.0'
out = ROOT / 'work' / (('abi-reference-' if args.reference_only else 'abi-') + args.arch) / args.optimization
out.mkdir(parents=True, exist_ok=True)
runtime = ROOT / 'work' / ('runtime-' + args.arch)
runtime.mkdir(parents=True, exist_ok=True)
(runtime / 'libgcc_tm.h').write_text('/* Arithmetic probe needs no extra target headers. */\n')
record = {'target': args.arch, 'optimization': args.optimization,
          'patches_sha256': patch_hashes(ROOT), 'compiler_sha256': None if args.reference_only else digest(build / 'cc1'),
          'reference_only': args.reference_only, 'native_frontend': args.native_frontend,
          'fixtures_sha256': {f.name: digest(f) for f in (ROOT / 'tests').glob('abi*')},
          'compilations': [], 'steps': []}

def save():
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')

def compile_source(name, input_path, extra):
    command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2'] + extra + ['-S', str(input_path), '-o', str(out / (name + '.s'))]
    r = subprocess.run(command, capture_output=True, text=True)
    record['compilations'].append({'command': command, 'exitcode': r.returncode,
                                  'stdout': r.stdout, 'stderr': r.stderr})
    save()
    if r.returncode:
        raise SystemExit(r.stderr)

helpers = ['muldi3', 'divdi3', 'moddi3', 'divmoddi4', 'udivdi3', 'umoddi3',
           'udivmoddi4', 'ashldi3', 'ashrdi3', 'lshrdi3', 'clz']
if not args.reference_only:
    compile_source('modern-' + args.arch, ROOT / 'tests/abi-functions.c', ['-' + args.optimization, '-DPREFIX=modern_'])
    for name in helpers:
        compile_source(name, source / 'libgcc/libgcc2.c',
                       ['-fbuilding-libgcc', '-fno-stack-protector', '-Dinhibit_libc',
                        '-DIN_LIBGCC2', '-DIN_GCC', '-DHAVE_CONFIG_H', '-DL_' + name,
                        '-I' + str(runtime), '-I' + str(build),
                        '-I' + str(source / 'gcc'), '-I' + str(source / 'include')])
GuestAgent = runpy.run_path(str(args.agent_client))['GuestAgent']
with GuestAgent(str(args.socket), timeout=45) as guest:
    def run(name, command):
        if args.arch == 'hppa':
            command = command.replace('/bin/cc -arch hppa -static -nostdlib', '/bin/ld -arch hppa')
            command = command.replace('/bin/cc -arch hppa -static -traditional-cpp -E', '/bin/cc -arch i386 -static -traditional-cpp -E')
        r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(args.directory) + ' && ' + command], execution_timeout=90)
        row = {'name': name, 'command': command, 'exitcode': r.get('exitcode'),
               'stdout': r['stdout'].decode('ascii', errors='replace'),
               'stderr': r['stderr'].decode('ascii', errors='replace')}
        record['steps'].append(row)
        save()
        print(name + ': ' + row['stdout'] + row['stderr'], flush=True)
        if r.get('exitcode') != 0:
            raise SystemExit(name + ' failed')
    for f in (ROOT / 'tests').glob('abi*'):
        if f.suffix == '.c' and (args.arch == 'hppa' or args.reference_only):
            copy = out / f.name
            text = f.read_text()
            if args.reference_only and f.name == 'abi-main.c':
                text = text.replace('modern_', 'native_')
            if args.arch == 'hppa':
                text = '#undef __TARGET_ARCHITECTURE__\n#define __TARGET_ARCHITECTURE__ "hppa"\n' + text
            copy.write_text(text)
            record.setdefault('prepared_fixtures_sha256', {})[f.name] = digest(copy)
            guest.upload(copy, args.directory + '/' + f.name)
        else:
            guest.upload(f, args.directory + '/' + f.name)
    includes = '-nostdinc -I sdk33/usr/include -I sdk33/usr/include/ansi -I sdk33/usr/include/bsd'
    for name, file, extra in [('native-' + args.arch, 'abi-functions.c', '-DPREFIX=native_'),
                              ('main-' + args.arch, 'abi-main.c', '')]:
        run(name + ' preprocessing', '/bin/cc -arch ' + args.arch + ' -static -traditional-cpp -E ' + includes + ' ' + extra + ' ' + file + ' -o ' + name + '.i')
        run(name + ' compilation', shlex.quote(args.native_frontend) + ' -quiet -O2 ' + name + '.i -o ' + name + '.s')
        run(name + ' assembly', '/bin/as -arch ' + args.arch + ' ' + name + '.s -o ' + name + '.o')
    for name in ([] if args.reference_only else ['modern-' + args.arch] + helpers):
        guest.upload(out / (name + '.s'), args.directory + '/' + name + '.s')
        run(name + ' assembly', '/bin/as -arch ' + args.arch + ' ' + name + '.s -o ' + args.arch + '-' + name + '.o')
    run('refresh copied archives', '/bin/ranlib sdk33/lib/' + args.arch + '/libcc.a sdk33/lib/libsys_s.a')
    objects = 'main-{a}.o native-{a}.o '.format(a=args.arch)
    if not args.reference_only:
        objects += '{a}-modern-{a}.o '.format(a=args.arch) + ' '.join(args.arch + '-' + h + '.o' for h in helpers)
    run('3.3 SDK link', '/bin/cc -arch ' + args.arch + ' -static -nostdlib sdk33/lib/crt0.o ' + objects + ' sdk33/lib/' + args.arch + '/libcc.a sdk33/lib/libsys_s.a -o mixed-' + args.arch + '33')
    guest.download(args.directory + '/mixed-' + args.arch + '33', out / 'mixed33')
print('Prepared ' + args.arch + ' executable; target runtime execution remains required.')
