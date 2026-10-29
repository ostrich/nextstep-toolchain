#!/usr/bin/env python3
"""Check source/type DWARF round trips through the real Mach-O tools and GDB."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, default=ROOT / 'install/current')
    parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], action='append')
    parser.add_argument('--compiler-build', type=Path)
    parser.add_argument('--gdb', required=True, help='GDB with executable-relative debug-bundle support')
    parser.add_argument('--host-tools', type=Path, help='Candidate Mach-O tools for qualification')
    args = parser.parse_args()
    arches = args.arch or ['i386', 'm68k', 'sparc', 'hppa']
    if args.compiler_build and len(arches) != 1:
        parser.error('A candidate compiler build requires exactly one architecture')
    output = args.output.resolve()
    if output.exists():
        parser.error('Use a fresh output directory')
    output.mkdir(parents=True)
    bundle = args.toolchain.resolve()
    source = output / 'source-lines.c'
    source.write_text('''volatile int debugger_result;
struct sample { int count; double value; };
__attribute__((noinline)) int compute(struct sample *sample, int delta)
{
    int before = sample->count;
    sample->count = before + delta;
    debugger_result = sample->count;
    return before;
}
int main(void)
{
    struct sample sample = { 7, 2.5 };
    int previous = compute(&sample, 5);
    return previous == 7 && debugger_result == 12 ? 0 : 1;
}
''')
    record = {'schema': 1, 'toolchain_manifest_sha256': digest(bundle / 'toolchain.json'),
              'source_sha256': digest(source), 'targets': {},
              'sdk_libsys_sha256': digest(args.sdk.resolve() / 'lib/libsys_s.a'),
              'debug_bundle_helper_sha256': digest(ROOT / 'tools/nextstep-debug.py'),
              'driver_sha256': digest(ROOT / 'tools/nextstep-gcc' if args.compiler_build
                                      else bundle / 'bin/nextstep-gcc')}
    if args.host_tools:
        record['candidate_host_tools_sha256'] = digest(
            args.host_tools.resolve().parent / 'build-record.json')
    if args.compiler_build:
        record['candidate_compiler'] = json.loads(
            (args.compiler_build / 'build-record.json').read_text())
    for arch in arches:
        directory = output / arch
        directory.mkdir()
        compiler = [str(bundle / 'bin/nextstep-gcc')]
        if args.compiler_build:
            compiler = [str(ROOT / 'tools/nextstep-gcc'), '--compiler-build',
                        str(args.compiler_build.resolve()), '--host-tools',
                        str((args.host_tools or bundle / 'libexec/cctools').resolve())]
        compiler += ['--sdk', str(args.sdk.resolve()), '-arch', arch,
                     '-O2', '-gdwarf-4', '-ffile-prefix-map=' + str(output) + '=.']
        target = {'steps': [], 'passed': True}
        record['targets'][arch] = target
        for name, options, suffix in [('assembly', ['-S'], '.s'),
                                       ('object', ['-c'], '.o'), ('executable', [], '')]:
            artifact = directory / ('source-lines' + suffix)
            input_file = directory / 'source-lines.o' if name == 'executable' else source
            command = compiler + options + [str(input_file), '-o', str(artifact)]
            step = {'name': name, 'command': command}
            target['steps'].append(step)
            try:
                result = subprocess.run(command, capture_output=True, timeout=120)
                step['exit_code'] = result.returncode
                (directory / (name + '.log')).write_bytes(result.stdout + result.stderr)
                if result.returncode:
                    target['passed'] = False
                    break
                step['sha256'] = digest(artifact)
                if name == 'assembly':
                    if b'__debug_info' not in artifact.read_bytes():
                        raise RuntimeError('Compiler silently omitted debug information')
                    continue
                commands = ['set pagination off', 'set confirm off', 'set auto-load off',
                            'file ' + str(artifact), 'info line compute',
                            'ptype struct sample', 'info address debugger_result']
                command = [args.gdb, '-q', '-nx', '-batch']
                for expression in commands:
                    command += ['-ex', expression]
                result = subprocess.run(command, capture_output=True, timeout=60)
                text = result.stdout + result.stderr
                (directory / (name + '-gdb.log')).write_bytes(text)
                step['gdb_command'] = command
                step['gdb_exit_code'] = result.returncode
                step['gdb_passed'] = (result.returncode == 0 and b'Line ' in text
                                      and b'int count;' in text and b'double value;' in text
                                      and b'debugger_result' in text and b'No line' not in text)
                if not step['gdb_passed']:
                    target['passed'] = False
                    break
            except (subprocess.TimeoutExpired, OSError, RuntimeError) as error:
                step['error'] = str(error)
                target['passed'] = False
                break
        print(arch + ': ' + ('PASS' if target['passed'] else 'FAIL'), flush=True)
        (output / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if all(row['passed'] for row in record['targets'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
