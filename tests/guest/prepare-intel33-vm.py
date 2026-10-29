#!/usr/bin/env python3
"""Prepare a private NS3.3 Intel CD-root test VM using its original IDE driver."""
import argparse
import json
from pathlib import Path
import sys
import shutil
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_inputs import digest
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--iso', type=Path, required=True)
p.add_argument('--boot-floppy', type=Path, required=True)
p.add_argument('--lab', type=Path, required=True)
p.add_argument('--qemu', type=Path, required=True)
p.add_argument('--nextufs', required=True)
p.add_argument('--probes', type=Path, default=ROOT / 'work/host-toolchain-tests')
p.add_argument('--probe', action='append', help='Probe filename to stage; repeatable, replaces the default suite')
a = p.parse_args()
lab = a.lab.resolve()
if lab.exists(): p.error('Use a new lab directory')
tool = shutil.which(a.nextufs)
if tool is None: p.error('nextufs executable not found')
probes = a.probes.resolve()
names = a.probe or ['runtime', 'archive-test', 'cxx', 'objc']
if len(names) != len(set(names)) or any(Path(n).name != n or n in ('.', '..') for n in names):
    p.error('Probe names must be unique plain filenames')
for path in [a.iso, a.boot_floppy, a.qemu, *[probes / name for name in names]]:
    if not path.is_file(): p.error('Missing input: ' + str(path))
config_path = '/private/Drivers/i386/System.config/Instance0.table'
old = subprocess.check_output([tool, 'browse', '--raw', str(a.boot_floppy), config_path])
if b'"Version" = "3.30";' not in old or b'"Install Mode" = "Yes";' not in old:
    p.error('Expected the original NS3.3 Intel installation boot floppy')
lab.mkdir(parents=True)
subprocess.run(['cp', '--reflink=auto', str(a.iso.resolve()), str(lab / 'root.raw')], check=True)
shutil.copyfile(a.boot_floppy, lab / 'boot.img')
config = '''"Version" = "3.30";
"Boot Drivers" = "PS2Keyboard EISABus PCIBus IDE";
"Active Drivers" = "";
"Kernel" = "hd(0,a)mach_kernel";
"Kernel Flags" = "-v -s rootdev=hd0a";
"Boot Graphics" = "No";
"Install Mode" = "No";
"Ask For Drivers" = "No";
"Language" = "English";
"Prompt For Driver Disk" = "No";
"APM" = "No";
'''
(lab / 'boot.table').write_text(config)
subprocess.run([tool, 'mkfile', '--unlink', str(lab / 'boot.img'), config_path], check=True, stdout=subprocess.DEVNULL)
subprocess.run([tool, 'mkfile', '--from-file', str(lab / 'boot.img'), config_path, str(lab / 'boot.table')], check=True, stdout=subprocess.DEVNULL)
for name in names:
    subprocess.run([tool, 'mkfile', '--from-file', str(lab / 'root.raw'), '/' + name, str(probes / name)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([tool, 'mkfile', '--chmod', str(lab / 'root.raw'), '/' + name, '0755'], check=True, stdout=subprocess.DEVNULL)
    if subprocess.check_output([tool, 'browse', '--raw', str(lab / 'root.raw'), '/' + name]) != (probes / name).read_bytes():
        raise SystemExit('Probe readback mismatch: ' + name)
command = [str(a.qemu.resolve()), '-name', 'nextstep33-intel-test', '-machine', 'pc,acpi=off,hpet=off,usb=off',
           '-accel', 'tcg', '-cpu', '486', '-m', '64', '-drive',
           'file=boot.img,if=floppy,format=raw,readonly=on', '-drive',
           'file=root.raw,if=ide,format=raw', '-boot', 'order=a', '-display', 'none',
           '-nic', 'none', '-serial', 'none', '-monitor', 'none', '-qmp',
           'unix:qmp.sock,server=on,wait=off', '-no-reboot', '-no-shutdown']
(lab / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
(lab / 'inputs.json').write_text(json.dumps({'iso_sha256': digest(a.iso), 'floppy_sha256': digest(a.boot_floppy),
                                           'probes': {n: digest(probes / n) for n in names}}, indent=2) + '\n')
(lab / 'run.py').write_text('import json, subprocess\nfrom pathlib import Path\np=Path(__file__).resolve().parent\nsubprocess.run(json.loads((p/"command.json").read_text()),cwd=p,check=True)\n')
print('Prepared ' + str(lab))
print('Start run.py, then use the single-user console. Root is mounted read-only.')
print('Run the staged probes from the single-user console, then /usr/etc/halt.')

print('For write tests on this disposable copy: /etc/mount -n -o remount,rw /dev/hd0a /')
