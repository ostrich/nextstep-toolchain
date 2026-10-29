#!/usr/bin/env python3
"""Build the experimental optimized NEXTSTEP C++ runtime against a private SDK."""
import argparse
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from build_inputs import digest, patch_hashes

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], default='i386')
    parser.add_argument('--compiler-build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--host-tools', type=Path, default=ROOT / 'work/host-tools/bin')
    parser.add_argument('--phase', choices=['configure', 'supc++', 'all'], default='all')
    parser.add_argument('--atomic-build', type=Path, help='Matching upstream libatomic build, required by SPARC native threads')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    sdk, compiler, output = (p.resolve() for p in (args.sdk, args.compiler_build, args.output))
    host_tools = args.host_tools.resolve()
    if not (host_tools / 'ar').is_file():
        raise SystemExit('Build the current host tools, including the matching BSD ar, first.')
    source = ROOT / 'work' / ('gcc-' + json.loads((ROOT / 'sources.lock.json').read_text())['gcc']['version'])
    macro_command = [str(compiler / 'gcc/xgcc'), '-B' + str(compiler / 'gcc') + '/',
                     '-dM', '-E', '-x', 'c', '/dev/null']
    macros = subprocess.check_output(macro_command, text=True)
    if '#define __USING_SJLJ_EXCEPTIONS__ 1' not in macros:
        raise SystemExit('This development runtime builder currently requires an SJLJ compiler.')
    model = subprocess.run([str(compiler / 'gcc/xgcc'), '-B' + str(compiler / 'gcc') + '/', '-v'],
                           capture_output=True, text=True, check=True)
    thread_model = next((line.removeprefix('Thread model: ') for line in model.stderr.splitlines()
                         if line.startswith('Thread model: ')), None)
    if thread_model not in ('single', 'nextstep'):
        raise SystemExit('Expected the single or native nextstep thread model.')
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'Makefile').is_file():
        # GCC target libraries disable ordinary header dependency tracking.
        # Reusing old objects after a configure/header change is unsafe.
        with (output / 'clean.log').open('wb') as log:
            subprocess.run(['make', 'clean'], cwd=output, check=True,
                           stdout=log, stderr=subprocess.STDOUT)
    headers = output / 'runtime-include'
    headers.mkdir(exist_ok=True)
    shutil.copyfile(source / 'libgcc/unwind-generic.h', headers / 'unwind.h')
    driver = [str(ROOT / 'tools/nextstep-gcc'), '--sdk', str(sdk), '-arch', args.arch,
              '--compiler-build', str(compiler), '--host-tools', str(host_tools)]
    launcher = output / 'cross-cc'
    launcher.write_text('#!/bin/sh\nexec ' + shlex.join(driver) + ' "$@"\n')
    launcher.chmod(0o755)
    env_values = {'CC': str(launcher), 'CXX': str(launcher),
                  'CFLAGS': '-O2', 'CXXFLAGS': '-O2',
                  'CPPFLAGS': shlex.join(['-I' + str(ROOT / 'nextstepcompat/include'), '-I' + str(headers)]),
                  'AR': str(host_tools / 'ar'), 'RANLIB': str(host_tools / 'ranlib'),
                  'LD': str(host_tools / 'ld'), 'LC_ALL': 'C', 'ZERO_AR_DATE': '1'}
    environment = dict(os.environ, **env_values)
    record = {'arch': args.arch, 'optimization': '-O2', 'phase': args.phase,
              'thread_model': thread_model,
              'host_tools_sha256': {name: digest(host_tools / name)
                  for name in ['ar', 'ranlib', 'as-' + args.arch, 'ld']},
              'compiler_sha256': {name: digest(compiler / 'gcc' / name)
                                  for name in ['xgcc', 'cc1', 'cc1plus']},
              'patches_sha256': patch_hashes(ROOT), 'environment': env_values, 'steps': [],
              'compatibility_sha256': {str(path.relative_to(ROOT)): digest(path)
                  for path in sorted((ROOT / 'runtime').rglob('*')) if path.is_file()}}
    # SJLJ uses compiler-built-in setjmp and needs no architecture-specific
    # DWARF register mappings. Keep host feature probes out of target code.
    auxiliary = output / 'unwind-include'
    auxiliary.mkdir(exist_ok=True)
    (auxiliary / 'tconfig.h').write_text('#define USED_FOR_TARGET\n')
    (auxiliary / 'tm.h').write_text('/* No SJLJ register mapping overrides. */\n')
    (auxiliary / 'libgcc_tm.h').write_text('/* No target runtime overrides. */\n')
    shutil.copyfile(source / ('libgcc/gthr-' + thread_model + '.h'), auxiliary / 'gthr-default.h')
    shutil.copyfile(auxiliary / 'gthr-default.h', headers / 'gthr-default.h')
    compatibility = output / 'nextstepcompat'
    compatibility_command = [sys.executable, str(ROOT / 'nextstepcompat/build.py'),
        '--sdk', str(sdk), '--arch', args.arch, '--cc', shlex.join(driver),
        '--tools', str(host_tools), '--output', str(compatibility)]
    with (output / 'nextstepcompat.log').open('wb') as log:
        result = subprocess.run(compatibility_command, stdout=log, stderr=subprocess.STDOUT)
    record['steps'].append({'command': compatibility_command, 'exitcode': result.returncode})
    (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if result.returncode:
        raise SystemExit('NextStepCompat failed; inspect nextstepcompat.log')
    compatibility_record = json.loads((compatibility / 'build-record.json').read_text())
    record['nextstepcompat_sha256'] = compatibility_record['sources_sha256']
    compatibility_archive = compatibility / args.arch / 'libnextstepcompat.a'
    record['artifacts'] = {'libnextstepcompat.a': digest(compatibility_archive)}
    units = [('unwind-sjlj', source / 'libgcc/unwind-sjlj.c')]
    if thread_model == 'nextstep':
        units += [('emutls', source / 'libgcc/emutls.c')]
    units += [('atexit-compat', ROOT / 'runtime/atexit-compat.c')]
    if thread_model == 'nextstep':
        units += [('gthread-compat', ROOT / 'runtime/threads/cthreads.c')]
    if args.arch == 'hppa':
        units += [('hppa-sync', source / 'libgcc/config/pa/sync-libfuncs.c')]
    units += [('crt-nextstep', ROOT / 'runtime/fp-startup.c')]
    objects = {}
    for name, unit in units:
        obj = output / (name + '.o')
        command = driver + ['-O2', '-c', '-fbuilding-libgcc']
        if name in ('unwind-sjlj', 'emutls'):
            command += ['-Dinhibit_libc']
        command += ['-I' + str(path) for path in [ROOT / 'nextstepcompat/include', auxiliary,
                     headers, source / 'libgcc', source / 'gcc', source / 'include']]
        command += [str(unit), '-o', str(obj)]
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
        record['steps'].append({'command': command, 'exitcode': result.returncode})
        (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise SystemExit(name + ' failed; inspect its log')
        objects[name] = obj
    exception_units = ['unwind-sjlj'] + (['emutls'] if thread_model == 'nextstep' else [])
    compatibility_units = [name for name in objects
                           if name not in exception_units and name != 'crt-nextstep']
    for name, unit_names in [('libgcc_eh.a', exception_units),
                             ('libnextstep-cxx-compat.a', compatibility_units)]:
        members = [objects[unit] for unit in unit_names]
        archive = output / name
        archive.unlink(missing_ok=True)
        command = [str(host_tools / 'libtool'), '-static', '-o', str(archive), *map(str, members)]
        subprocess.run(command, check=True)
        record.setdefault('artifacts', {})[name] = digest(archive)
    (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    record['artifacts']['crt-nextstep.o'] = digest(output / 'crt-nextstep.o')
    if thread_model == 'nextstep':
        # Configure's real link probes need the thread bridge, unwinder and FP
        # entry point together. Keep raw objects out of libtool's LIBS input.
        bootstrap = output / 'libnextstep-configure.a'
        bootstrap.unlink(missing_ok=True)
        subprocess.run([str(host_tools / 'libtool'), '-static', '-o', str(bootstrap),
                        *map(str, objects.values()),
                        *map(str, sorted((compatibility / args.arch / 'objects').glob('*.o')))], check=True)
        record['artifacts'][bootstrap.name] = digest(bootstrap)
        environment['LIBS'] = str(bootstrap)
    else:
        environment['LIBS'] = str(output / 'libnextstep-cxx-compat.a') + ' ' + str(compatibility_archive)
    if args.atomic_build:
        atomic_library = args.atomic_build.resolve() / '.libs/libatomic.a'
        if not atomic_library.is_file():
            raise SystemExit('Missing matching libatomic archive: ' + str(atomic_library))
        environment['LIBS'] += ' ' + str(atomic_library)
        record['libatomic_sha256'] = digest(atomic_library)
    record['environment']['LIBS'] = environment['LIBS']
    commands = [('configure', output, [str(source / 'libstdc++-v3/configure'),
                '--build=x86_64-pc-linux-gnu', '--host=' + args.arch + '-next-nextstep3.3',
                '--disable-shared', '--enable-static', '--disable-multilib',
                '--disable-nls', '--disable-libstdcxx-pch'])]
    if args.phase != 'configure':
        commands.append(('build', output / 'libsupc++' if args.phase == 'supc++' else output,
                         ['make', '-j' + str(args.jobs), 'LIBS=', 'all']))
    for name, cwd, command in commands:
        print(name + ': ' + str(output / (name + '.log')), flush=True)
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT)
        record['steps'].append({'command': command, 'cwd': str(cwd), 'exitcode': result.returncode})
        (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise SystemExit(name + ' failed; inspect ' + str(output / (name + '.log')))
        if name == 'configure':
            # libstdc++ deliberately clears MAKEOVERRIDES in recursive makes,
            # so a command-line LIBS= does not reach its library link steps.
            # Keep bootstrap archives in the configure probes, then clear only
            # this variable in generated build files. Preserve all target flags.
            changed = []
            for makefile in sorted(output.rglob('Makefile')):
                text = makefile.read_text()
                text, count = re.subn(r'^LIBS[ \t]*=.*$', 'LIBS =', text, flags=re.M)
                if count:
                    makefile.write_text(text)
                    changed.append(str(makefile.relative_to(output)))
            record['configure_only_libraries'] = environment['LIBS']
            record['build_only_overrides'] = {'LIBS': '', 'generated_makefiles': changed}
            (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    if args.phase != 'configure':
        record['artifacts']['libsupc++.a'] = digest(output / 'libsupc++/.libs/libsupc++.a')
        if args.phase == 'all':
            record['artifacts']['libstdc++.a'] = digest(output / 'src/.libs/libstdc++.a')
            for module in ['std', 'std.compat']:
                unit = output / ('src/c++23/' + module + '.cc')
                if unit.stat().st_size < 1000:
                    raise SystemExit('The upstream module build silently discarded ' + module)
                record['artifacts'][module + '.cc'] = digest(unit)
        (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Requested build phase completed. Guest execution is a separate validation gate.')


if __name__ == '__main__':
    main()
