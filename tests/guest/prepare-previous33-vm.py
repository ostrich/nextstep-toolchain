#!/usr/bin/env python3
"""Prepare a disposable Previous NS3.3 batch from a clean stopped lab."""
import argparse
import json
import os
from pathlib import Path
import sys
import re
import shlex
import shutil
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_inputs import digest

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--disk', type=Path, help='Optional clean stopped disk; keep launcher/config from baseline')
p.add_argument('--lab', type=Path, required=True)
p.add_argument('--probe', action='append', required=True, help='NAME=HOST_FILE; repeatable')
p.add_argument('--asset', action='append', default=[], help='NAME=HOST_FILE companion data or program; copy without running')
p.add_argument('--nextufs', required=True)
p.add_argument('--display', type=int, default=193)
p.add_argument('--emulator', type=Path, help='Previous executable; defaults to previous on PATH')
p.add_argument('--discard-test-outputs', action='store_true', help='Remove old fixture stdout/stderr/status files only from the disposable copy')
p.add_argument('--timeout', type=int, default=180, help='Guest seconds per probe')
a = p.parse_args()
base, lab = a.baseline.resolve(), a.lab.resolve()
emulator = (a.emulator or Path(shutil.which('previous') or '/usr/bin/previous')).resolve()
if not emulator.is_file() or not os.access(emulator, os.X_OK):
    p.error('--emulator must name an executable file')
tool = Path(a.nextufs).resolve()
if not tool.is_file() or not os.access(tool, os.X_OK):
    p.error('--nextufs must name an executable file')
a.nextufs = str(tool)
if lab.exists(): p.error('Use a new lab directory')
if a.timeout < 10 or not 1 <= a.display <= 999: p.error('Invalid timeout or X display')
config = base / 'home/.config/previous/previous.cfg'
disk = (a.disk or base / 'disk.img').resolve()
for name in [config, disk, base / 'launch.py']:
    if not name.is_file(): p.error('Missing baseline input: ' + str(name))
q = subprocess.run(['fuser', '-s', str(disk)], capture_output=True)
if q.returncode != 1: p.error('Baseline disk may be open; stop its VM first')
probes, assets = {}, {}
for item, destination in ([(x, probes) for x in a.probe] +
                          [(x, assets) for x in a.asset]):
    name, separator, source = item.partition('=')
    if not separator or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..') or name in probes or name in assets:
        p.error('Expected unique plain NAME=FILE')
    path = Path(source).resolve()
    if not path.is_file(): p.error('Missing probe: ' + str(path))
    destination[name] = path
lab.mkdir(parents=True)
subprocess.run(['cp', '--reflink=auto', str(disk), str(lab / 'disk.img')], check=True)
(lab / 'home/.config/previous').mkdir(parents=True)
shutil.copyfile(config, lab / 'home/.config/previous/previous.cfg')
(lab / 'share').mkdir()
launch = (base / 'launch.py').read_text()
# Baselines can themselves be previously prepared labs with another display.
# Replace only literal X display values and the associated readiness pathname.
launch = re.sub(r"':[0-9]+'", repr(':' + str(a.display)), launch)
launch = re.sub(r'(?<=/tmp/\.X11-unix/X)[0-9]+', str(a.display), launch)
launch = ("from pathlib import Path\n"
          "if not (Path(__file__).resolve().parent / 'inputs.json').is_file():\n"
          " raise SystemExit('VM preparation did not complete')\n" + launch)
if emulator != Path('/usr/bin/previous').resolve():
    marker = "'--chdir','/mnt'"
    if launch.count(marker) != 1:
        p.error('Baseline launcher changed; cannot safely select another emulator')
    launch = launch.replace(marker, "'--ro-bind',"+repr(str(emulator))+",'/usr/bin/previous',\n "+marker)
(lab / 'launch.py').write_text(launch)
# Release only known test-owned files on the copied image. CG0 inode space is
# tighter than total free space in this old filesystem.
listing = subprocess.check_output([a.nextufs, 'browse', str(lab / 'disk.img'), '/port-test'], text=True)
existing = set(re.findall(r"name='([^']+)'", listing))
for name in ['runtime', 'libc', 'archive-test', 'cxx', 'objc', 'run.sh', 'final-suite.txt',
             'matrix-results.txt', 'results.txt', 'first-host-tools-results.txt',
             'libc-fat', 'runtime-fat', 'final-results.txt', 'trace.gdb']:
    if name in existing:
        subprocess.run([a.nextufs, 'mkfile', '--unlink', str(lab / 'disk.img'), '/port-test/' + name],
                       check=True, stdout=subprocess.DEVNULL)
cleared = []
if a.discard_test_outputs:
    # Old fixture logs exhaust CG0 inodes before the image runs out of bytes.
    # These are known test-owned outputs, never source fixtures or guest files.
    text = subprocess.check_output([a.nextufs, 'browse', str(lab / 'disk.img'),
                                    '/port-test/fixtures'], text=True)
    for name in re.findall(r"name='([^']+)'", text):
        if re.fullmatch(r'[A-Za-z0-9_.-]+\.(stdout|stderr|status)', name):
            subprocess.run([a.nextufs, 'mkfile', '--unlink', str(lab / 'disk.img'),
                            '/port-test/fixtures/' + name], check=True, stdout=subprocess.DEVNULL)
            cleared.append(name)
script = '''#!/bin/sh
PATH=/bin:/usr/bin:/usr/ucb:/usr/etc; export PATH
cd /port-test
exec > results.txt 2>&1
echo 'CXX RUNTIME BEGIN'
'''
script += 'for test in ' + ' '.join(shlex.quote(n) for n in probes) + '; do\n'
script += ''' echo "RUN $test"
 ./$test /port-test /sdmach &
 child=$!
 (sleep TIMEOUT; kill -9 "$child" 2>/dev/null) &
 guard=$!
 wait "$child"
 result=$?
 kill "$guard" 2>/dev/null
 echo "EXIT $test $result"
done
echo 'CXX RUNTIME END'
sync
/usr/etc/halt
'''.replace('TIMEOUT', str(a.timeout))
(lab / 'run.sh').write_text(script)
for name, path in [*probes.items(), *assets.items(), ('run.sh', lab / 'run.sh')]:
    guest = '/port-test/' + name
    subprocess.run([a.nextufs, 'mkfile', '--from-file', str(lab / 'disk.img'), guest, str(path)],
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run([a.nextufs, 'mkfile', '--chmod', str(lab / 'disk.img'), guest, '0755'],
                   check=True, stdout=subprocess.DEVNULL)
    if subprocess.check_output([a.nextufs, 'browse', '--raw', str(lab / 'disk.img'), guest]) != path.read_bytes():
        raise SystemExit('Probe readback mismatch: ' + name)
rc = subprocess.check_output([a.nextufs, 'browse', '--raw', str(lab / 'disk.img'), '/private/etc/rc.local'])
if b'/bin/sh /port-test/run.sh &' not in rc: raise SystemExit('Expected baseline batch hook in rc.local')
(lab / 'inputs.json').write_text(json.dumps({'baseline_disk_sha256': digest(disk),
    'previous_executable': str(emulator), 'previous_sha256': digest(emulator), 'display': a.display,
    'probes': {n: digest(f) for n, f in probes.items()},
    'assets': {n: digest(f) for n, f in assets.items()},
    'batch_sha256': digest(lab / 'run.sh'), 'discarded_test_outputs': cleared}, indent=2) + '\n')
print('Prepared ' + str(lab) + '. Launch launch.py; collect results only after native halt.')
