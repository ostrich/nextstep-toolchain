#!/usr/bin/env python3
"""Check direct, multiple-unit and archive DWARF links and relocated bundles."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--compiler-build', type=Path, required=True)
    parser.add_argument('--host-tools', type=Path, required=True)
    parser.add_argument('--gdb', type=Path, required=True)
    parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tools = args.host_tools.resolve()
    cc = [str(ROOT / 'tools/nextstep-gcc'), '--compiler-build',
          str(args.compiler_build.resolve()), '--host-tools', str(tools),
          '--sdk', str(args.sdk.resolve()), '-arch', args.arch, '-O2', '-gdwarf-4',
          '-ffile-prefix-map=' + str(out) + '=.']
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
    record = {'arch': args.arch, 'steps': [], 'passed': False}

    def run(name, command):
        result = subprocess.run(command, capture_output=True, timeout=120)
        (out / (name + '.log')).write_bytes(result.stdout + result.stderr)
        record['steps'].append({'name': name, 'command': [str(x) for x in command],
                                'exit_code': result.returncode})
        if result.returncode:
            raise RuntimeError(name + ' failed')
        return result.stdout + result.stderr

    try:
        for stem in ['first', 'second']:
            run(stem, cc + ['-c', str(out / (stem + '.c')), '-o', str(out / (stem + '.o'))])
        run('archive', [str(tools / 'libtool'), '-static', '-o', str(out / 'first.a'),
                        str(out / 'first.o')])
        run('link', cc + [str(out / 'second.o'), str(out / 'first.a'), '-o', str(out / 'program')])
        moved = out / 'moved'
        moved.mkdir()
        shutil.move(out / 'program', moved / 'program')
        shutil.move(out / 'program.debug', moved / 'program.debug')
        # Remove all original object/archive inputs; only the retained bundle
        # may satisfy the executable's map after relocation.
        for name in ['first.o', 'second.o', 'first.a']:
            (out / name).unlink()
        command = [str(args.gdb.resolve()), '-q', '-nx', '-batch',
                   '-ex', 'set auto-load off', '-ex', 'file ' + str(moved / 'program')]
        for query in ['info line first_function', 'info line second_function',
                      'ptype struct first_type', 'ptype struct second_type',
                      'info address first_value', 'info address second_value']:
            command += ['-ex', query]
        text = run('gdb', command)
        if (text.count(b'Line ') != 2 or b'double weight;' not in text
                or b'long values[3];' not in text or b'No line' in text
                or b'warning:' in text):
            raise RuntimeError('GDB did not read both compilation units cleanly')
        record['passed'] = True
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        record['error'] = str(error)
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print(args.arch + ': ' + ('PASS' if record['passed'] else 'FAIL'))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
