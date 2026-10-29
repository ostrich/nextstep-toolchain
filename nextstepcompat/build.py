#!/usr/bin/env python3
"""Build optimized NextStepCompat static libraries with a NeXT cross compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ARCHES = ['i386', 'm68k', 'sparc', 'hppa']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    compiler = p.add_mutually_exclusive_group(required=True)
    compiler.add_argument('--toolchain', type=Path, help='Installed compiler bundle')
    compiler.add_argument('--cc', help='Bootstrap nextstep-gcc command, shell-quoted but never shell-executed')
    p.add_argument('--tools', type=Path, help='Classic Mach-O tools directory, required with --cc')
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--arch', choices=ARCHES, action='append')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--shared', action='store_true', help='Build canonical shared-runtime intermediates')
    a = p.parse_args()
    arches = list(dict.fromkeys(a.arch or ARCHES))
    output, sdk = a.output.resolve(), a.sdk.resolve()
    if output == ROOT or ROOT in output.parents:
        p.error('Build outside the maintained source component')
    if a.cc and not a.tools:
        p.error('--cc requires --tools')
    tc = a.toolchain.resolve() if a.toolchain else None
    tools = a.tools.resolve() if a.tools else tc / 'libexec/cctools'
    cc = shlex.split(a.cc) if a.cc else [str(tc / 'bin/nextstep-gcc')]
    env = dict(os.environ, LC_ALL='C', ZERO_AR_DATE='1')
    output.mkdir(parents=True, exist_ok=True)
    sources = {str(n.relative_to(ROOT)): digest(n) for n in sorted(ROOT.rglob('*'))
               if n.is_file() and '__pycache__' not in n.parts}
    record = {'name': 'NextStepCompat', 'version': (ROOT / 'VERSION').read_text().strip(),
              'canonical_shared': a.shared,
              'sources_sha256': sources, 'targets': {}, 'steps': []}
    record_path = output / 'build-record.json'

    def run(cmd, log):
        with log.open('wb') as stream:
            r = subprocess.run(list(map(str, cmd)), env=env, stdout=stream, stderr=subprocess.STDOUT)
        record['steps'].append({'command': list(map(str, cmd)), 'exitcode': r.returncode})
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        if r.returncode:
            raise SystemExit('NextStepCompat failed; inspect ' + str(log))

    # Preserve pristine imported sources and prove maintained adapters match
    # the recorded, replayable release patches before compiling.
    options = ROOT / 'options'
    pin = json.loads((options / 'sources.json').read_text())
    for name, expected in pin['files_sha256'].items():
        if digest(options / name) != expected:
            raise SystemExit('Pinned option/math source mismatch: ' + name)
    replay = output / 'options-replay'
    replay.mkdir(exist_ok=True)
    for name in ['getopt.c', 'getopt_long.c', 'round.c', 'floorf.c']:
        shutil.copyfile(options / name, replay / name)
    for patch in ['0001-nextstep-option-state-and-stdio.patch', '0002-nextstep-round-support.patch', '0003-nextstep-floorf-support.patch']:
        result = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(options / patch)], cwd=replay, capture_output=True)
        if result.returncode: raise SystemExit('Option/math adapter patch failed: ' + patch)
    for original, adapter in [('getopt.c', 'getopt.c'), ('getopt_long.c', 'getopt_long.c'), ('round.c', 'round-compat.c'), ('floorf.c', 'floorf-compat.c')]:
        if (replay / original).read_bytes() != (ROOT / 'src' / adapter).read_bytes():
            raise SystemExit('Option/math adapter differs from its patch: ' + adapter)

    prepared = output / 'prepared'
    prepared.mkdir(exist_ok=True)
    for directory, name, patch in [
        ('format', 'vfprintf.c', '0001-nextstep-bounded-output.patch'),
        ('parse', 'floatscan.c', '0001-nextstep-string-input.patch')]:
        pin = json.loads((ROOT / directory / 'sources.json').read_text())
        if digest(ROOT / directory / name) != pin['source_sha256']:
            raise SystemExit('Pinned source mismatch: ' + directory)
        dest = prepared / directory
        dest.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / directory / name, dest / name)
        if directory == 'parse':
            for header in ['parse-support.h', 'binary-scale.h']:
                shutil.copyfile(ROOT / directory / header, dest / header)
        run(['patch', '-d', dest, '-p1', '--batch', '--fuzz=0', '-i', ROOT / directory / patch],
            output / (directory + '-patch.log'))

    run(['patch', '-d', prepared / 'format', '-p1', '--batch', '--fuzz=0', '-i',
         ROOT / 'format/0002-nextstep-stream-output.patch'], output / 'format-stream-patch.log')

    regex = ROOT / 'regex'
    regex_pin = json.loads((regex / 'sources.json').read_text())
    regex_dest = prepared / 'regex'
    regex_dest.mkdir(exist_ok=True)
    for name, expected in regex_pin['files_sha256'].items():
        if digest(regex / name) != expected:
            raise SystemExit('Pinned regex source mismatch: ' + name)
        shutil.copyfile(regex / name, regex_dest / name)
    run(['patch', '-d', regex_dest, '-p1', '--batch', '--fuzz=0', '-i',
         regex / '0001-nextstep-single-byte-regex.patch'], output / 'regex-patch.log')
    run(['patch', '-d', regex_dest, '-p1', '--batch', '--fuzz=0', '-i',
         regex / '0002-single-byte-collating-elements.patch'], output / 'regex-collation-patch.log')

    scan = ROOT / 'scan'
    scan_pin = json.loads((scan / 'sources.json').read_text())
    scan_dest = prepared / 'scan'
    scan_dest.mkdir(exist_ok=True)
    for name, expected in scan_pin['files_sha256'].items():
        if digest(scan / name) != expected:
            raise SystemExit('Pinned scan source mismatch: ' + name)
        shutil.copyfile(scan / name, scan_dest / name)
    for name in ['scan-support.h', 'stream.c']:
        shutil.copyfile(scan / name, scan_dest / name)
    shutil.copyfile(ROOT / 'parse/binary-scale.h', scan_dest / 'binary-scale.h')
    run(['patch', '-d', scan_dest, '-p1', '--batch', '--fuzz=0', '-i',
         scan / '0001-nextstep-native-streams.patch'], output / 'scan-patch.log')

    time_source = ROOT / 'time'
    time_pin = json.loads((time_source / 'sources.json').read_text())
    time_dest = prepared / 'time'
    time_dest.mkdir(exist_ok=True)
    for name, expected in time_pin['files_sha256'].items():
        if digest(time_source / name) != expected:
            raise SystemExit('Pinned time source mismatch: ' + name)
        shutil.copyfile(time_source / name, time_dest / name)
    shutil.copyfile(time_source / 'time-support.h', time_dest / 'time-support.h')
    run(['patch', '-d', time_dest, '-p1', '--batch', '--fuzz=0', '-i',
         time_source / '0001-nextstep-time-formatting.patch'], output / 'time-patch.log')

    network_pin = json.loads((ROOT / 'network/sources.json').read_text())
    network_dest = prepared / 'network'
    network_dest.mkdir(exist_ok=True)
    for name, expected in network_pin['files_sha256'].items():
        if digest(ROOT / 'network' / name) != expected:
            raise SystemExit('Pinned network conversion source mismatch: ' + name)
        shutil.copyfile(ROOT / 'network' / name, network_dest / name)
    run(['patch', '-d', network_dest, '-p1', '--batch', '--fuzz=0', '-i',
         ROOT / 'network/0001-nextstep-ipv4-conversions.patch'], output / 'network-patch.log')

    math_source = ROOT / 'math'
    math_pin = json.loads((math_source / 'sources.json').read_text())
    math_dest = prepared / 'math'
    math_dest.mkdir(exist_ok=True)
    for name, expected in math_pin['files_sha256'].items():
        if digest(math_source / name) != expected:
            raise SystemExit('Pinned math source mismatch: ' + name)
        shutil.copyfile(math_source / name, math_dest / name)
    shutil.copyfile(math_source / 'math-support.h', math_dest / 'math-support.h')
    run(['patch', '-d', math_dest, '-p1', '--batch', '--fuzz=0', '-i',
         math_source / '0001-nextstep-math-support.patch'], output / 'math-patch.log')

    units = {n.stem: n for n in sorted((ROOT / 'src').glob('*.c'))}
    units.update({'math-' + n.stem: n for n in sorted(math_dest.glob('*.c'))})
    units.update({'network-' + n.stem: n for n in sorted(network_dest.glob('*.c'))})
    units.update({'time-' + n.stem: n for n in sorted(time_dest.glob('*.c'))})
    units.update({'format-compat': prepared / 'format/vfprintf.c',
                  'floating-conversion': prepared / 'parse/floatscan.c'})
    string_pin = json.loads((ROOT / 'string/sources.json').read_text())
    for name, expected in string_pin['files_sha256'].items():
        if digest(ROOT / 'string' / name) != expected:
            raise SystemExit('Pinned string source mismatch: ' + name)
        if name.endswith('.c'):
            units['string-' + Path(name).stem] = ROOT / 'string' / name
    units.update({'scan-' + n.stem: n for n in sorted(scan_dest.glob('*.c'))})
    units.update({'regex-' + n.stem: n for n in sorted(regex_dest.glob('*.c'))})
    allocation = ROOT / 'format/allocation'
    allocation_pin = json.loads((allocation / 'sources.json').read_text())
    for name, expected in allocation_pin['files_sha256'].items():
        if digest(allocation / name) != expected:
            raise SystemExit('Pinned allocation source mismatch: ' + name)
        if name.endswith('.c'):
            units['format-' + Path(name).stem] = allocation / name
    libraries = []
    for arch in arches:
        dest = output / arch
        objects = dest / 'objects'
        objects.mkdir(parents=True, exist_ok=True)
        members = []
        for name, source in units.items():
            obj = objects / (name + '.o')
            cmd = cc + ['--sdk', str(sdk), '-arch', arch, '--compat-headers', str(ROOT / 'include'),
                        '-O2', '-std=gnu17', '-c', str(source), '-o', str(obj)]
            if a.shared:
                cmd += ['-fno-common', '-fno-zero-initialized-in-bss', '--shared-exports', str(ROOT / 'shared.json'), '-DNS33_SHARED_RUNTIME']
            if name in ('string-strdup', 'string-strndup', 'format-vasprintf'):
                cmd += ['-Dmalloc=ns33_compat_malloc']
            run(cmd, dest / (name + '.log'))
            members.append(obj)
        archive = dest / 'libnextstepcompat.a'
        archive.unlink(missing_ok=True)
        run([tools / 'libtool', '-static', '-o', archive, *members], dest / 'archive.log')
        record['targets'][arch] = {'archive_sha256': digest(archive),
                                   'objects_sha256': {n.name: digest(n) for n in members}}
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        libraries.append(archive)
        print('Built NextStepCompat: ' + arch, flush=True)
    if len(arches) > 1:
        fat = output / 'libnextstepcompat.a'
        run([tools / 'lipo', '-create', *libraries, '-output', fat], output / 'fat.log')
        record['fat_archive_sha256'] = digest(fat)
    record['status'] = 'passed'
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    print('Build complete; target execution remains a separate check.')


if __name__ == '__main__':
    main()
