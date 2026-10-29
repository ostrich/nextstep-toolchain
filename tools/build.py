#!/usr/bin/env python3
"""Build the experimental Linux-hosted NeXT compiler (assembly output only)."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
    parser.add_argument('--languages', default='c', help='comma-separated c,c++,objc,obj-c++ frontends')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--output', type=Path, help='Separate experimental build directory')
    parser.add_argument('--thread-model', choices=['single', 'nextstep'], default='single')
    parser.add_argument('--exception-model', choices=['default', 'sjlj', 'dwarf'], default='default')
    args = parser.parse_args()
    if not set(args.languages.split(',')) <= {'c', 'c++', 'objc', 'obj-c++'} or 'c' not in args.languages.split(','):
        parser.error('--languages must include c and contain only supported frontends')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    gcc = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']
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
    if args.exception_model != 'default':
        configure.append('--enable-sjlj-exceptions=' + ('yes' if args.exception_model == 'sjlj' else 'no'))
    host_flags='-O2 -g0 -ffile-prefix-map=' + str(ROOT) + '=SOURCE'
    env = dict(os.environ, LC_ALL='C', CFLAGS=host_flags, CXXFLAGS=host_flags)
    record = {'arch': args.arch, 'languages': args.languages.split(','),
              'exception_model': args.exception_model, 'thread_model': args.thread_model,
              'patches_sha256': patch_hashes(ROOT), 'source_archive_sha256': gcc['sha256'], 'host_cflags': host_flags}
    for name, command in [('configure', configure),
                          ('build', ['make', '-j' + str(args.jobs), 'all-gcc'])]:
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
