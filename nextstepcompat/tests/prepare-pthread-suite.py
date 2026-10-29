#!/usr/bin/env python3
"""Build one hashed NIHS pthread payload, retaining the older regression suites."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'compat', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--shared', action='store_true')
p.add_argument('--failures', type=Path)
p.add_argument('--upstream', type=Path)
p.add_argument('--old-consumer', type=Path)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
payload = out / 'payload'
payload.mkdir()
for source in ['pthread-native', 'pthread-native-spin', 'threads', 'thread-keys', 'pthread-expanded', 'pthread-exit', 'pthread-cxx']:
    destination = out / source
    command = [sys.executable, str(HERE / 'build-threads.py'),
               '--toolchain', str(a.toolchain.resolve()), '--sdk', str(a.sdk.resolve()),
               '--compat', str(a.compat.resolve()), '--output', str(destination),
               '--source', source]
    if a.shared:
        command.append('--shared')
    subprocess.run(command, check=True)
    shutil.copyfile(destination / 'threads', payload / source)
if a.shared:
    shutil.copyfile(a.compat / 'libnextstepcompat.1.shlib', payload / 'libnextstepcompat.1.shlib')
script = '''#!/bin/sh
case "$0" in */*) payload=`echo "$0" | /bin/sed 's|/[^/]*$||'` ;; *) payload=. ;; esac
cd "$payload" || exit 90
if test -f libnextstepcompat.1.shlib; then
  /bin/cp libnextstepcompat.1.shlib /usr/local/lib/libnextstepcompat.1.shlib.pthread-test || exit 91
  /bin/mv /usr/local/lib/libnextstepcompat.1.shlib.pthread-test /usr/local/lib/libnextstepcompat.1.shlib || exit 92
fi
'''
for source in ['pthread-native', 'pthread-native-spin', 'threads', 'thread-keys', 'pthread-expanded', 'pthread-exit', 'pthread-cxx']:
    script += './' + source + ' || exit 1\n'
if a.failures:
    shutil.copyfile(a.failures, payload / 'pthread-failures')
    script += './pthread-failures || exit 2\n'
if a.old_consumer:
    shutil.copyfile(a.old_consumer, payload / 'old-consumer')
    script += './old-consumer || exit 3\n'
if a.upstream:
    selected = 0
    for executable in sorted(a.upstream.glob('pthread_*')):
        if executable.name.count('-') != 2:
            continue
        # Fat test names end in -1-1; per-architecture slices add a suffix.
        if not executable.name.endswith('-1-1'):
            continue
        selected += 1
        shutil.copyfile(executable, payload / executable.name)
        script += 'echo UPSTREAM ' + executable.name + '\n'
        script += './' + executable.name + ' || exit 4\n'
    if selected != 8:
        raise SystemExit('Expected eight built Open POSIX tests')
    script += 'echo "PASS selected Open POSIX pthread tests"\n'
script += 'echo PORTS-SUITE 0\n'
(payload / 'run.sh').write_text(script)
for f in payload.iterdir():
    f.chmod(0o755)
(out / 'payload.json').write_text(json.dumps(
    {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in payload.iterdir()},
    indent=2) + '\n')
