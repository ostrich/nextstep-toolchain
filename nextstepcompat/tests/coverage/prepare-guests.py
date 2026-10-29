#!/usr/bin/env python3
"""Prepare isolated four-target API audit guests using the existing VM helpers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True, help='Completed audit/finish output')
    p.add_argument('--lab', type=Path, required=True)
    p.add_argument('--nextufs', type=Path, required=True)
    p.add_argument('--intel-iso', type=Path, required=True)
    p.add_argument('--intel-floppy', type=Path, required=True)
    p.add_argument('--qemu-i386', type=Path, required=True)
    p.add_argument('--previous-baseline', type=Path, required=True)
    p.add_argument('--risc-iso', type=Path, required=True)
    p.add_argument('--display', type=int, default=207)
    a = p.parse_args()
    out, lab, tool = (x.resolve() for x in (a.output, a.lab, a.nextufs))
    if lab.exists():
        p.error('Use a new lab directory')
    record = json.loads((out / 'results.json').read_text())
    payloads = {}
    for arch, modes in record['results'].items():
        names = ['api-batch'] + [mode + '-' + name for mode, data in modes.items()
                 for name, t in data['tests'].items() if t['build'] == 'passed']
        payloads[arch] = {name: out / arch / name for name in names}
        for path in payloads[arch].values():
            if not path.is_file():
                p.error('Missing executable: ' + str(path))
    if set(payloads) != {'i386', 'm68k', 'sparc', 'hppa'}:
        p.error('Preparation requires all four target builds')
    lab.mkdir(parents=True)
    commands = []

    def run(cmd):
        cmd = list(map(str, cmd))
        commands.append(cmd)
        subprocess.run(cmd, check=True)

    def put(image, guest, path):
        run([tool, 'mkfile', '--from-file', image, guest, path])
        run([tool, 'mkfile', '--chmod', image, guest, '0755'])
        if subprocess.check_output([str(tool), 'browse', '--raw', str(image), guest]) != path.read_bytes():
            raise SystemExit('Payload readback mismatch: ' + guest)

    cmd = [sys.executable, ROOT / 'tests/guest/prepare-intel33-vm.py',
           '--iso', a.intel_iso, '--boot-floppy', a.intel_floppy, '--qemu', a.qemu_i386,
           '--lab', lab / 'intel33', '--nextufs', tool, '--probes', out / 'i386']
    for name in [*payloads['i386'], 'run.sh']:
        cmd += ['--probe', name]
    run(cmd)
    # The CD-root helper starts read-only. The wrapper must remount its own copy.
    script = lab / 'intel-run.sh'
    script.write_text('#!/bin/sh\n/etc/mount -n -o remount,rw /dev/hd0a / || exit 2\n'
                      'cd /\n./api-batch > /api-results.txt 2>&1\n/bin/cat /api-results.txt\n'
                      '/bin/sync\n/usr/etc/halt\n')
    put(lab / 'intel33/root.raw', '/api-run.sh', script)
    cmd = [sys.executable, ROOT / 'tests/guest/prepare-previous33-vm.py',
           '--baseline', a.previous_baseline, '--lab', lab / 'previous33',
           '--nextufs', tool, '--display', a.display, '--timeout', '300', '--discard-test-outputs',
           '--probe', 'api-batch=' + str(payloads['m68k']['api-batch'])]
    for name, path in payloads['m68k'].items():
        if name != 'api-batch':
            cmd += ['--asset', name + '=' + str(path)]
    run(cmd)
    cmd = [sys.executable, PROJECT / 'host/qemu/tests/risc/prepare-validation-cd.py',
           '--lab', lab / 'risc33', '--iso', a.risc_iso, '--probes', ROOT / 'work',
           '--nextufs', tool, '--only-extras', '--writable-root']
    for arch in ('sparc', 'hppa'):
        cmd += ['--extra', arch + ':api-batch=' + str(payloads[arch]['api-batch'])]
    run(cmd)
    image = lab / 'risc33/media/ns33-validation.iso'
    for arch in ('sparc', 'hppa'):
        for name, path in payloads[arch].items():
            if name != 'api-batch':
                put(image, '/gcc-tests/' + arch + '/' + name, path)
        d = lab / 'risc33' / (arch + '-validation')
        d.mkdir()
        run([tool, 'mkimg', d / 'report.raw', '128M'])
    (lab / 'preparation.json').write_text(json.dumps({
        'commands': commands,
        'payloads': {arch: {n: hashlib.sha256(f.read_bytes()).hexdigest()
                           for n, f in files.items()} for arch, files in payloads.items()},
        'build_results_sha256': hashlib.sha256((out / 'build-results.json').read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print('Prepared isolated guests:', lab)


if __name__ == '__main__':
    main()
