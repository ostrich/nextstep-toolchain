#!/usr/bin/env python3
"""Compare host runtime objects with the original assembler on a build guest."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import tarfile
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['i386', 'm68k', 'sparc', 'hppa'], required=True)
p.add_argument('--socket', required=True)
p.add_argument('--agent-client', type=Path, required=True,
               help='Python transport module exposing GuestAgent')
a = p.parse_args()
if not a.agent_client.is_file():
    p.error('--agent-client must name an existing Python module')
d = ROOT / 'work' / ('runtime-host-' + a.arch)
archive = d / 'reference-input.tar'
with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as t:
    for f in sorted(d.glob('*.s')):
        t.add(f, arcname=f.name)
Agent = runpy.run_path(str(a.agent_client))['GuestAgent']
remote = '/private/tmp/assembler-reference-' + a.arch
with Agent(a.socket, timeout=60) as guest:
    guest.upload(archive, remote + '.tar')
    command = ('test -d {d} || mkdir {d}; cd {d} && /usr/bin/gnutar xf ../assembler-reference-{a}.tar '
               '&& for f in *.s; do /bin/as -arch {a} "$f" -o "`basename "$f" .s`.o" || exit 1; done '
               '&& /usr/bin/gnutar cf ../assembler-reference-{a}-objects.tar *.o').format(d=remote, a=a.arch)
    result = guest.execute('/bin/sh', ['-c', command], execution_timeout=120)
    if result['exitcode']:
        raise SystemExit(result['stderr'].decode(errors='replace'))
    guest.download(remote + '-objects.tar', d / 'reference-objects.tar')
rows = []
with tarfile.open(d / 'reference-objects.tar') as t:
    for member in t:
        if not member.isfile() or Path(member.name).name != member.name:
            raise SystemExit('Unexpected reference archive member')
        original = t.extractfile(member).read()
        host = (d / member.name).read_bytes()
        rows.append({'member': member.name, 'identical': original == host,
                     'native_sha256': hashlib.sha256(original).hexdigest(),
                     'host_sha256': hashlib.sha256(host).hexdigest()})
(d / 'assembler-comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
print(a.arch + ': ' + str(sum(row['identical'] for row in rows)) + '/' + str(len(rows)) + ' objects identical')
if not all(row['identical'] for row in rows):
    raise SystemExit('Differences require inspection: ' + ', '.join(row['member'] for row in rows if not row['identical']))
