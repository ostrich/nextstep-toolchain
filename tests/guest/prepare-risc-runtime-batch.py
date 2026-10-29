#!/usr/bin/env python3
"""Stage a combined RISC runtime batch on private report disks."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--lab', type=Path, required=True)
p.add_argument('--iso', type=Path, required=True)
p.add_argument('--fixtures', type=Path, required=True)
p.add_argument('--additional', type=Path, required=True)
p.add_argument('--flatc-sparc', type=Path, required=True)
p.add_argument('--flatc-hppa', type=Path, required=True)
p.add_argument('--re2c-root', type=Path, required=True, help='ARCH/re2c and ARCH/re2c-runner build outputs')
p.add_argument('--report-template', type=Path, required=True)
p.add_argument('--nextufs', required=True)
p.add_argument('--risc-preparer', type=Path, required=True,
               help='External RISC validation-CD preparation script')
a = p.parse_args()
if not a.risc_preparer.is_file():
    p.error('--risc-preparer must name an existing Python script')
tool = shutil.which(a.nextufs)
if not tool:
    p.error('nextufs executable not found')
if a.lab.exists():
    p.error('Use a new lab directory')
if subprocess.run(['fuser', str(a.report_template)], capture_output=True).returncode == 0:
    p.error('Report template is in use')
basic = ['abi', 'stdlib', 'threads', 'atomics', 'objects-only', 'c-smoke', 'objcxx']
extra = ['floating-conversion', 'floating-immediates', 'numeric-cxx', 'c99-cxx', 'flatc-runner']
inputs = {}
for arch in ('sparc', 'hppa'):
    files = {n: a.fixtures / arch / n for n in basic}
    files.update({n: a.additional / arch / n for n in extra})
    files['flatc'] = getattr(a, 'flatc_' + arch)
    for name in ('re2c', 're2c-runner'):
        files[name] = a.re2c_root / arch / name
    files['runtime-batch'] = a.additional / arch / 'runtime-batch'
    for path in files.values():
        if not path.is_file():
            p.error('Missing input: ' + str(path))
    inputs[arch] = files
command = [sys.executable, str(a.risc_preparer.resolve()),
           '--lab', str(a.lab.resolve()), '--iso', str(a.iso.resolve()),
           '--probes', str(ROOT / 'work'), '--nextufs', tool, '--only-extras', '--writable-root']
for arch in inputs:
    command += ['--extra', arch + ':runtime-batch=' + str(inputs[arch]['runtime-batch'].resolve())]
    for arg in ('/private/tmp/gcc-batch', '/private/tmp', '/mach_kernel'):
        command += ['--argument', arch + ':runtime-batch=' + arg]
subprocess.run(command, check=True)

def mutate(*args):
    subprocess.run([tool, 'mkfile', *map(str, args)], check=True, stdout=subprocess.DEVNULL)

records = {}
for arch, files in inputs.items():
    d = a.lab / (arch + '-validation')
    d.mkdir()
    report = d / 'report.raw'
    subprocess.run(['cp', '--reflink=auto', str(a.report_template.resolve()), str(report)], check=True)
    with (d / 'report-preparation.log').open('wb') as log:
        subprocess.run([tool, 'fsck', '-n', str(report)], stdout=log, stderr=subprocess.STDOUT, check=True)
    mutate('--mkdir', report, '/gcc-batch')
    records[arch] = {}
    for name, path in files.items():
        if name == 'runtime-batch':
            continue
        target = '/gcc-batch/' + name
        mutate('--from-file', report, target, path.resolve())
        mutate('--chmod', report, target, '0755')
        data = subprocess.check_output([tool, 'browse', '--raw', str(report), target])
        if data != path.read_bytes():
            raise SystemExit('Payload readback mismatch: ' + arch + '/' + name)
        records[arch][name] = hashlib.sha256(data).hexdigest()
(a.lab / 'payload-inputs.json').write_text(json.dumps(records, indent=2) + '\n')
print('Prepared both private report disks; start run-validation.py for each target.')
