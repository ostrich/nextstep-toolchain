#!/usr/bin/env python3
"""Build the experimental Linux-hosted NeXT compiler (assembly output only)."""
import argparse
import json
import os
import shlex
from pathlib import Path
import subprocess
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
    parser.add_argument('--languages', default='c', help='comma-separated c,c++,objc,obj-c++ frontends')
    parser.add_argument('--build-target-compiler', type=Path,
                        help='Build-host compiler for the same NeXT target, needed for Canadian builds')
    parser.add_argument('--host', help='Optional compiler execution host triplet for a Canadian cross build')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--output', type=Path, help='Separate experimental build directory')
    parser.add_argument('--thread-model', choices=['single', 'nextstep'], default='single')
    parser.add_argument('--exception-model', choices=['default', 'sjlj', 'dwarf'], default='default')
    args = parser.parse_args()
    if not set(args.languages.split(',')) <= {'c', 'c++', 'objc', 'obj-c++'} or 'c' not in args.languages.split(','):
        parser.error('--languages must include c and contain only supported frontends')
    if args.host and not args.build_target_compiler:
        parser.error('--host requires --build-target-compiler')
    if args.build_target_compiler and not args.build_target_compiler.is_file():
        parser.error('Build target compiler does not exist')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    gcc = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']
    if args.build_target_compiler:
        bootstrap = args.build_target_compiler.resolve()
        query = [str(bootstrap), '-B' + str(bootstrap.parent) + '/']
        target = subprocess.check_output(query + ['-dumpmachine'], text=True).strip()
        version = subprocess.check_output(query + ['-dumpfullversion'], text=True).strip()
        if target != args.arch + '-next-nextstep3.3' or version != gcc['version']:
            parser.error('Build target compiler must match the selected target and GCC version')
    source = ROOT / 'work' / ('gcc-' + gcc['version'])
    if not (source / 'gcc/config' / ('pa' if args.arch == 'hppa' else args.arch) / 'nextstep.h').exists():
        raise SystemExit('Run tools/prepare.py --patched first.')
    build = args.output.resolve() if args.output else ROOT / 'work' / ('build-' + args.arch)
    build.mkdir(parents=True, exist_ok=True)
    stub = ROOT / 'tools/target-tool-unavailable'
    configure = [os.path.relpath(source / 'configure', build), '--prefix=/opt/nextstep-toolchain', '--target=' + args.arch + '-next-nextstep3.3',
                 '--disable-bootstrap', '--disable-multilib', '--disable-nls',
                 '--enable-languages=' + args.languages, '--without-headers',
                 '--disable-libsanitizer', '--disable-libssp', '--disable-libquadmath',
                 '--disable-libgomp', '--disable-libatomic', '--disable-libstdcxx',
                 '--disable-libvtv', '--with-as=' + os.path.relpath(stub, build / 'gcc'), '--with-ld=' + os.path.relpath(stub, build / 'gcc'),
                 '--without-gnu-as', '--without-gnu-ld', '--enable-threads=' + args.thread_model]
    if args.host:
        configure += ['--build=' + subprocess.check_output([str(source / 'config.guess')], text=True).strip(),
                      '--host=' + args.host]
    if args.exception_model != 'default':
        configure.append('--enable-sjlj-exceptions=' + ('yes' if args.exception_model == 'sjlj' else 'no'))
    host_flags='-O2 -g0 -ffile-prefix-map=' + str(ROOT) + '=SOURCE'
    env = dict(os.environ, LC_ALL='C', CFLAGS=host_flags, CXXFLAGS=host_flags)
    record = {'arch': args.arch, 'host': args.host, 'languages': args.languages.split(','),
              'exception_model': args.exception_model, 'thread_model': args.thread_model,
              'patches_sha256': patch_hashes(ROOT), 'source_archive_sha256': gcc['sha256'], 'host_cflags': host_flags}
    make_args = ['make', '-j' + str(args.jobs), 'all-gcc']
    if args.build_target_compiler:
        bootstrap = args.build_target_compiler.resolve()
        make_args.append('GCC_FOR_TARGET=' + shlex.join([str(bootstrap), '-B' + str(bootstrap.parent) + '/']))
        record['build_target_compiler_sha256'] = digest(args.build_target_compiler.resolve())
    for name, command in [('configure', configure),
                          ('build', make_args)]:
        print(f'{name}: writing {build}/{name}.log', flush=True)
        with (build / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, cwd=build, env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        record[name] = {'command': command, 'exit_code': result.returncode}
        (build / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise SystemExit(f'{name} failed: inspect its log')
    frontends = {'c': 'cc1', 'c++': 'cc1plus', 'objc': 'cc1obj', 'obj-c++': 'cc1objplus'}
    names = ['xgcc'] + [frontends[language] for language in args.languages.split(',')]
    record['compiler_sha256'] = {name: digest(build / 'gcc' / name) for name in names}
    (build / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Built assembly-output-only compiler; no target runtime installed.')

if __name__ == '__main__':
    main()
