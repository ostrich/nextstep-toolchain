#!/usr/bin/env python3
"""Prototype canonical function references using renamed assembly definitions.

This is an investigation fixture, not an alternate production constructor.
It uses the maintained constructor and leaves NIHS consumers for runtime tests.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
tc, sdk, out = [path.resolve() for path in [a.toolchain, a.sdk, a.output]]
out.mkdir(parents=True, exist_ok=False)
steps = []
def run(*command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    steps.append({'command': list(map(str, command)), 'exitcode': result.returncode,
                  'stdout': result.stdout, 'stderr': result.stderr})
    (out / 'commands.json').write_text(json.dumps(steps, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout
prefix = '_ns33_entry_body'
names = ['_example', '_get_example']
source = out / 'library.c'
source.write_text('''struct record {int (*operation)(int);};
int example(int n) { return n + 3; }
int (*get_example(void))(int) { return example; }
const struct record exported_record = { example };
''')
consumer = out / 'consumer.c'
consumer.write_text('''#include <stdio.h>
struct record {int (*operation)(int);};
extern const struct record exported_record;
extern int example(int);
extern int (*ns33_entry_body_get_example(void))(int);
int main(void) {
 int (*function)(int) = ns33_entry_body_get_example();
 int a = function == example, b = exported_record.operation == example;
 int c = function(7) == 10 && exported_record.operation(8) == 11;
 printf("canonical entry getter %d table %d calls %d\\n", a,b,c);
 return !(a && b && c);
}
''')
consumers = []
results = {}
for arch in ['m68k', 'i386', 'hppa', 'sparc']:
    d = out / arch
    d.mkdir()
    assembly = d / 'library.s'
    run(tc / 'bin/nextstep-gcc', '--sdk', sdk, '-arch', arch, '-O2', '-S', source, '-o', assembly)
    text = assembly.read_text()
    for name in names:
        text, count = re.subn(r'(?m)^' + re.escape(name) + r':', prefix + name + ':', text)
        assert count == 1, (arch, name, count)
        text, count = re.subn(r'(?m)^(\s*\.globl\s+)' + re.escape(name) + r'\s*$',
                             r'\g<1>' + prefix + name, text)
        assert count == 1, (arch, name, count)
    assembly.write_text(text)
    run(tc / ('libexec/cctools/as-' + arch), '-o', d / 'library.o', assembly)
    spec = {'install_name': '/usr/local/lib/libentrytest.1.shlib', 'minor_version': 1,
            'addresses': {'text': '0x2a800000', 'data': '0x2a900000'},
            'segment_reservation': '0x100000', 'exports': [prefix + name for name in names],
            'data_exports': [{'name': '_exported_record', 'kind': 'const', 'slot_size': 256}]}
    (d / 'spec.json').write_text(json.dumps(spec, indent=2) + '\n')
    addresses = {name: 0 for name in names}
    branch_values = None
    for phase in ['probe', 'final']:
        stage = d / phase
        stage.mkdir()
        (stage / 'public.s').write_text(''.join('.globl ' + name + '\n' + name +
                                              ' = ' + hex(value) + '\n' for name, value in addresses.items()))
        run(tc / ('libexec/cctools/as-' + arch), '-o', stage / 'public.o', stage / 'public.s')
        run(tc / 'bin/nextstep-shlib', '--sdk', sdk, '--arch', arch,
            '--spec', d / 'spec.json', '--output', stage / 'runtime.shlib',
            '--import-library', stage / 'import.a', '--build-record', stage / 'build.json',
            d / 'library.o', stage / 'public.o')
        symbols = run(tc / 'libexec/cctools/nm', '-g', stage / 'import.a')
        values = {fields[2]: int(fields[0], 16) for line in symbols.splitlines()
                  if len(fields := line.split()) == 3 and fields[1] == 'A'}
        current = {name: values[prefix + name] for name in names}
        if branch_values is not None:
            assert current == branch_values, (arch, current, branch_values)
        branch_values = current
        addresses = current
    # Public entry aliases plus the regular import give this investigation's
    # consumer the canonical addresses. A production implementation must emit
    # these aliases in the import itself and hide the private body names.
    run(tc / 'bin/nextstep-gcc', '--sdk', sdk, '-arch', arch, '-O2', consumer,
        d / 'final/public.o', d / 'final/import.a', '-o', d / 'consumer')
    results[arch] = {'addresses': addresses, 'runtime_tested': False}
    consumers.append(d / 'consumer')
    print('PASS canonical entry construction ' + arch)
run(tc / 'libexec/cctools/lipo', '-create', *consumers, '-output', out / 'consumer')
run(tc / 'libexec/cctools/lipo', '-create',
    *[out / arch / 'final/runtime.shlib' for arch in results], '-output', out / 'libentrytest.1.shlib')
(out / 'host-validation.json').write_text(json.dumps({'status': 'passed', 'targets': results}, indent=2) + '\n')
