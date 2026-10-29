#!/usr/bin/env python3
"""Run mixed compiler ABI tests on an explicitly selected disposable guest.

The optional --sdk33 test requires the original 3.3 SDK and Intel libcc.a
already under guest --directory. It executes the result on the selected guest,
which does not substitute for testing on NEXTSTEP 3.3.
This uses the project guest agent only as a transport, not as a build dependency.
"""
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

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--socket', required=True, type=Path)
    p.add_argument('--agent-client', type=Path, required=True,
                   help='Python transport module exposing GuestAgent')
    p.add_argument('--directory', default='/private/tmp/gcc16-abi')
    p.add_argument('--native-frontend', help='guest path to the original Intel 3.3 cc1obj frontend')
    p.add_argument('--sdk33', action='store_true', help='also link the private 3.3 SDK and execute on this guest')
    p.add_argument('--optimization', choices=['O1', 'O2', 'O3', 'Os'], default='O2')
    args = p.parse_args()
    agent_file = args.agent_client
    if not agent_file.is_file():
        p.error('--agent-client must name an existing Python module')
    GuestAgent = runpy.run_path(str(agent_file))['GuestAgent']
    build = ROOT / 'work/build-i386/gcc'
    result_dir = ROOT / ('work/abi-native33' if args.native_frontend else 'work/abi') / args.optimization
    result_dir.mkdir(parents=True, exist_ok=True)
    command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-' + args.optimization,
               '-DPREFIX=modern_', '-S', str(ROOT / 'tests/abi-functions.c'),
               '-o', str(result_dir / 'modern.s')]
    subprocess.run(command, check=True)
    runtime = ROOT / 'work/runtime-i386'
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / 'libgcc_tm.h').write_text('/* Initial arithmetic probe needs no extra runtime target headers. */\n')
    source = ROOT / 'work/gcc-16.2.0'
    helpers = ['divdi3', 'moddi3', 'divmoddi4']
    helper_commands = []
    for helper in helpers:
        helper_command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2',
                          '-fbuilding-libgcc', '-fno-stack-protector', '-Dinhibit_libc',
                          '-DIN_LIBGCC2', '-DIN_GCC', '-DHAVE_CONFIG_H', '-DL_' + helper,
                          '-I' + str(runtime), '-I' + str(build),
                          '-I' + str(source / 'gcc'), '-I' + str(source / 'include'),
                          '-S', str(source / 'libgcc/libgcc2.c'),
                          '-o', str(runtime / (helper + '.s'))]
        subprocess.run(helper_command, check=True)
        helper_commands.append(helper_command)
    records = {'compiler_command': command, 'helper_commands': helper_commands,
               'compiler_sha256': digest(build / 'cc1'),
               'patches_sha256': patch_hashes(ROOT),
               'test_sha256': {f.name: digest(f) for f in (ROOT / 'tests').glob('abi*')},
               'steps': []}
    with GuestAgent(str(args.socket), timeout=45) as guest:
        def run(label, text, expected=None):
            r = guest.execute('/bin/sh', ['-c', 'cd ' + shlex.quote(args.directory) + ' && ' + text], execution_timeout=90)
            entry = {'name': label, 'command': text,
                     'stdout': r['stdout'].decode('ascii', errors='replace'),
                     'stderr': r['stderr'].decode('ascii', errors='replace'),
                     'exitcode': r.get('exitcode'), 'signal': r.get('signal')}
            records['steps'].append(entry)
            (result_dir / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
            print(label + ': ' + entry['stdout'] + entry['stderr'], flush=True)
            if r.get('exitcode') != 0 or (expected is not None and entry['stdout'].strip() != expected):
                raise SystemExit(label + ' failed')
        for source in (ROOT / 'tests').glob('abi*'):
            guest.upload(source, args.directory + '/' + source.name)
        guest.upload(result_dir / 'modern.s', args.directory + '/modern.s')
        if args.native_frontend:
            frontend = shlex.quote(args.native_frontend)
            sdk_flags = '-nostdinc -I sdk33/usr/include -I sdk33/usr/include/ansi -I sdk33/usr/include/bsd'
            run('3.3 reference preprocessing', '/bin/cc -arch i386 -static -traditional-cpp -E ' + sdk_flags + ' -DPREFIX=native_ abi-functions.c -o native.i && /bin/cc -arch i386 -static -traditional-cpp -E abi-main.c -o main.i')
            run('3.3 reference compilation', frontend + ' -quiet -O2 native.i -o native.s && ' + frontend + ' -quiet -O2 main.i -o main.s')
            run('3.3 reference assembly', '/bin/as -arch i386 native.s -o native.o && /bin/as -arch i386 main.s -o main.o')
        else:
            run('native reference objects', '/bin/cc -arch i386 -static -O2 -DPREFIX=native_ -c abi-functions.c -o native.o && /bin/cc -arch i386 -static -O2 -c abi-main.c -o main.o')
        for helper in helpers:
            guest.upload(runtime / (helper + '.s'), args.directory + '/' + helper + '.s')
            run('arithmetic runtime helper ' + helper, '/bin/as -arch i386 ' + helper + '.s -o ' + helper + '.o')
        run('NeXT assembler', '/bin/as -arch i386 modern.s -o modern.o')
        run('4.2 link', '/bin/cc -arch i386 main.o native.o modern.o divdi3.o moddi3.o divmoddi4.o -o mixed42')
        run('4.2 execution', './mixed42', expected='mixed ABI: 32 checks, 0 failures')
        guest.download(args.directory + '/mixed42', result_dir / 'mixed42')
        if args.sdk33:
            run('refresh copied SDK archive indexes', '/bin/ranlib libcc33.a sdk33/lib/libsys_s.a')
            run('3.3 SDK link', '/bin/cc -arch i386 -static -nostdlib sdk33/lib/crt0.o main.o native.o modern.o divdi3.o moddi3.o divmoddi4.o libcc33.a sdk33/lib/libsys_s.a -o mixed33')
            run('3.3 SDK execution on selected guest', './mixed33', expected='mixed ABI: 32 checks, 0 failures')
            guest.download(args.directory + '/mixed33', result_dir / 'mixed33')
    print('Passed mixed ABI tests on this guest; NEXTSTEP 3.3 execution remains separate.')

if __name__ == '__main__':
    main()
