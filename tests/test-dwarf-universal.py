#!/usr/bin/env python3
"""Qualify universal executables, object files and archives through GDB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCHES = ['i386', 'm68k', 'sparc', 'hppa']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--host-tools', type=Path, required=True)
    parser.add_argument('--gdb', type=Path, required=True)
    parser.add_argument('--compiler-build', action='append', required=True, metavar='ARCH=DIR')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    builds = {}
    for value in args.compiler_build:
        arch, separator, directory = value.partition('=')
        if not separator or arch not in ARCHES or arch in builds:
            parser.error('Supply one ARCH=DIR per NIHS architecture')
        builds[arch] = Path(directory).resolve()
    if set(builds) != set(ARCHES):
        parser.error('All four candidate compilers are required')
    out, tools = args.output.resolve(), args.host_tools.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'first.c').write_text('''struct first_type { int value; double weight; };
volatile struct first_type first_value = { 7, 2.5 };
__attribute__((noinline)) int first_function(void) { return first_value.value; }
''')
    (out / 'second.c').write_text('''struct second_type { char tag; long values[3]; };
volatile struct second_type second_value = { 2, { 3, 4, 5 } };
extern int first_function(void);
__attribute__((noinline)) int second_function(void) { return second_value.values[1]; }
int main(void) { return first_function() == 7 && second_function() == 4 ? 0 : 1; }
''')
    record = {'steps': [], 'passed': False}

    def run(name, command):
        command = list(map(str, command))
        result = subprocess.run(command, capture_output=True, timeout=120)
        (out / (name + '.log')).write_bytes(result.stdout + result.stderr)
        record['steps'].append({'name': name, 'command': command, 'exit_code': result.returncode})
        if result.returncode:
            raise RuntimeError(name + ' failed')
        return result.stdout + result.stderr

    def compiler(arch):
        return ['python3', ROOT / 'tools/nextstep-gcc', '--compiler-build', builds[arch],
                '--host-tools', tools, '--sdk', args.sdk.resolve(), '-arch', arch,
                '-O2', '-g', '-ffile-prefix-map=' + str(out) + '=.']

    try:
        for arch in ARCHES:
            directory = out / arch
            directory.mkdir()
            for name in ['first', 'second']:
                run(arch + '-' + name, compiler(arch) + ['-c', out / (name + '.c'),
                                                       '-o', directory / (name + '.o')])
            run(arch + '-archive', [tools / 'libtool', '-static', '-o', directory / 'first.a',
                                    directory / 'first.o'])
        for name in ['first.a', 'second.o']:
            run('fat-' + name, [tools / 'lipo', '-create',
                *[out / arch / name for arch in ARCHES], '-output', out / name])
        # Archive OSO timestamps describe members, not the archive file itself.
        os.utime(out / 'first.a', (1, 1))
        for arch in ARCHES:
            directory = out / arch
            run(arch + '-link', compiler(arch) + [out / 'second.o', out / 'first.a',
                                                '-o', directory / 'program'])
            shutil.copytree(directory / 'program.debug' / arch,
                            out / 'program.debug' / arch)
        run('fat-executable', [tools / 'lipo', '-create',
            *[out / arch / 'program' for arch in ARCHES], '-output', out / 'program'])
        (out / 'first.a').unlink()
        (out / 'second.o').unlink()
        for arch in ARCHES:
            shutil.rmtree(out / arch)
        for arch in ARCHES:
            architecture = 'hppa1.0' if arch == 'hppa' else arch
            command = [args.gdb.resolve(), '-q', '-nx', '-batch',
                       '-ex', 'set auto-load off', '-ex', 'set architecture ' + architecture,
                       '-ex', 'file ' + str(out / 'program')]
            for expression in ['info line first_function', 'info line second_function',
                               'ptype struct first_type', 'ptype struct second_type']:
                command += ['-ex', expression]
            text = run(arch + '-gdb', command)
            if (text.count(b'Line ') != 2 or b'double weight;' not in text
                    or b'long values[3];' not in text or b'warning:' in text):
                raise RuntimeError(arch + ': incomplete universal source/type reading')
        record['binary_sha256'] = hashlib.sha256((out / 'program').read_bytes()).hexdigest()
        record['passed'] = True
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        record['error'] = str(error)
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Universal executable/object/archive tests: ' + ('PASS' if record['passed'] else 'FAIL'))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
