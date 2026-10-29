#!/usr/bin/env python3
"""Batch classic Objective-C interoperability and bounded C++ frontend probes."""
import argparse
import json
from pathlib import Path
import sys
import runpy
import shlex
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--socket', type=Path, required=True)
p.add_argument('--native-frontend', default=None)
p.add_argument('--overlay', type=Path, default=ROOT / 'work/sdk-compat')
p.add_argument('--directory', default='/private/tmp/gcc16-abi')
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
args = p.parse_args()
if not args.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
if args.native_frontend is None:
    args.native_frontend = args.directory + '/reference-frontend' + ('' if args.arch == 'i386' else '-' + args.arch)
GuestAgent = runpy.run_path(str(args.agent_client))['GuestAgent']
build = ROOT / 'work' / ('build-' + args.arch) / 'gcc'
out = ROOT / 'work' / ('languages' if args.arch == 'i386' else 'languages-' + args.arch)
out.mkdir(parents=True, exist_ok=True)
sdk = args.sdk.resolve() / 'usr/include'
flags = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2', '-nostdinc',
         '-isystem', str(args.overlay.resolve()), '-isystem', str(build / 'include'),
         '-idirafter', str(sdk), '-idirafter', str(sdk / 'ansi'),
         '-idirafter', str(sdk / 'bsd')]
record = {'target': args.arch, 'execution_performed': args.arch == 'i386', 'compilations': [], 'steps': [], 'patches_sha256': patch_hashes(ROOT),
          'compiler_sha256': {name: digest(build / name) for name in ['cc1plus', 'cc1obj', 'cc1objplus']},
          'fixtures_sha256': {f.name: digest(f) for f in (ROOT / 'tests').glob('objc-*')}}

def save():
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')

def compile_source(name, source, extra):
    command = flags + extra + ['-S', str(ROOT / 'tests' / source), '-o', str(out / (name + '.s'))]
    r = subprocess.run(command, capture_output=True, text=True)
    record['compilations'].append({'name': name, 'command': command,
                                  'exitcode': r.returncode, 'stdout': r.stdout,
                                  'stderr': r.stderr})
    save()
    if r.returncode:
        raise SystemExit(name + ' compilation failed: ' + r.stderr)

with GuestAgent(str(args.socket), timeout=45) as guest:
    def run(name, command, expected=None):
        command = command.replace('-arch i386', '-arch ' + args.arch)
        if args.arch == 'hppa':
            command = command.replace('/bin/cc -arch hppa -static -nostdlib', '/bin/ld -arch hppa')
            command = command.replace('/bin/cc -arch hppa -static -traditional-cpp -E', '/bin/cc -arch i386 -static -traditional-cpp -E')
        if args.arch != 'i386':
            command = command.replace('libcc33.a', 'sdk33/lib/' + args.arch + '/libcc.a')
        r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(args.directory) + ' && ' + command], execution_timeout=90)
        entry = {'name': name, 'command': command, 'exitcode': r.get('exitcode'),
                 'stdout': r['stdout'].decode('ascii', errors='replace'),
                 'stderr': r['stderr'].decode('ascii', errors='replace')}
        record['steps'].append(entry)
        save()
        print(name + ': ' + entry['stdout'] + entry['stderr'], flush=True)
        if r.get('exitcode') != 0 or (expected and entry['stdout'].strip() != expected):
            raise SystemExit(name + ' failed')
    for path in (ROOT / 'tests').glob('objc-*'):
        if args.arch == 'hppa' and path.suffix == '.m':
            copy = out / path.name
            copy.write_text('#undef __TARGET_ARCHITECTURE__\n#define __TARGET_ARCHITECTURE__ "hppa"\n' + path.read_text())
            guest.upload(copy, args.directory + '/' + path.name)
        else:
            guest.upload(path, args.directory + '/' + path.name)
    if args.arch != 'i386':
        run('refresh copied archives', '/bin/ranlib sdk33/lib/' + args.arch + '/libcc.a sdk33/lib/libsys_s.a')
    native = shlex.quote(args.native_frontend)
    run('3.3 Objective-C preprocessing', '/bin/cc -arch i386 -static -traditional-cpp -E -nostdinc -I sdk33/usr/include -I sdk33/usr/include/ansi -I sdk33/usr/include/bsd -DPROBE_CLASS=NativeProbe -DPROBE_CHILD=NativeChild -DCHILD_DELTA=2 objc-class.m -o native-class.i')
    run('3.3 Objective-C compilation', native + ' -ObjC -quiet -O2 native-class.i -o native-class.s && /bin/as -arch i386 native-class.s -o native-class.o')
    for language, suffix in [('objective-c', 'objc'), ('objective-c++', 'objcxx')]:
        extra = ['-x' + language]
        if suffix == 'objcxx':
            extra += ['-fno-exceptions', '-fno-rtti']
        else:
            extra += ['-std=gnu11']
        compile_source(suffix + '-class', 'objc-class.m', extra + ['-DPROBE_CLASS=ModernProbe', '-DPROBE_CHILD=ModernChild', '-DCHILD_DELTA=1'])
        compile_source(suffix + '-main', 'objc-runtime.m', extra)
        for part in ['class', 'main']:
            name = suffix + '-' + part
            guest.upload(out / (name + '.s'), args.directory + '/' + name + '.s')
            run(name + ' assembly', '/bin/as -arch i386 ' + name + '.s -o ' + name + '.o')
        objects = 'native-class.o ' + suffix + '-class.o ' + suffix + '-main.o '
        for target in (['33', '42'] if args.arch == 'i386' else ['33']):
            binary = suffix + target
            if target == '33':
                link = '/bin/cc -arch i386 -static -nostdlib sdk33/lib/crt0.o ' + objects + 'libcc33.a sdk33/lib/libsys_s.a'
            else:
                link = '/bin/cc -arch i386 ' + objects
            run(binary + ' link', link + ' -o ' + binary)
            if args.arch == 'i386':
                run(binary + ' execution', './' + binary, 'objc runtime: 52 checks, 0 failures')
            guest.download(args.directory + '/' + binary, out / binary)
    for language, suffix in [('objective-c', 'strings'), ('objective-c++', 'stringsxx')]:
        extra = ['-x' + language]
        if suffix == 'stringsxx':
            extra += ['-fno-exceptions', '-fno-rtti']
        compile_source(suffix, 'objc-strings.m', extra)
        guest.upload(out / (suffix + '.s'), args.directory + '/' + suffix + '.s')
        run(suffix + ' assembly', '/bin/as -arch i386 ' + suffix + '.s -o ' + suffix + '.o')
        for target in (['33', '42'] if args.arch == 'i386' else ['33']):
            binary = suffix + target
            if target == '33':
                link = '/bin/cc -arch i386 -static -nostdlib sdk33/lib/crt0.o ' + suffix + '.o libcc33.a sdk33/lib/libsys_s.a'
            else:
                link = '/bin/cc -arch i386 ' + suffix + '.o'
            run(binary + ' link', link + ' -o ' + binary)
            if args.arch == 'i386':
                run(binary + ' execution', './' + binary, 'objc constants: passed')
            guest.download(args.directory + '/' + binary, out / binary)
    compile_source('cxx-constructors', 'cxx-constructors.cc', ['-fno-exceptions', '-fno-rtti'])
    guest.upload(out / 'cxx-constructors.s', args.directory + '/cxx-constructors.s')
    run('C++ constructor assembly', '/bin/as -arch i386 cxx-constructors.s -o cxx-constructors.o')
    for target in (['33', '42'] if args.arch == 'i386' else ['33']):
        binary = 'cxx' + target
        if target == '33':
            link = '/bin/cc -arch i386 -static -nostdlib sdk33/lib/crt0.o cxx-constructors.o libcc33.a sdk33/lib/libsys_s.a'
        else:
            link = '/bin/cc -arch i386 cxx-constructors.o'
        run(binary + ' link', link + ' -o ' + binary)
        if args.arch == 'i386':
            run(binary + ' execution', './' + binary, 'cxx probe: 1 42\ncxx destructor: 42')
        guest.download(args.directory + '/' + binary, out / binary)
print('Language probes passed on Intel; other CPUs are prepared for separate execution.' if args.arch == 'i386' else 'Language probes assembled/linked; target runtime execution remains required.')
