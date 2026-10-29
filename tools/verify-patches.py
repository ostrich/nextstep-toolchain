#!/usr/bin/env python3
"""Replay the ordered patches without fuzz and compare maintained source files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from build_inputs import digest, patch_hashes

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--full', action='store_true', help='Also verify every unpatched upstream file and reject extra files')
args = p.parse_args()
gcc = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']
version = 'gcc-' + gcc['version']
archive = ROOT / 'work/downloads' / (version + '.tar.xz')
if digest(archive) != gcc['sha256']:
    raise SystemExit('Release archive hash mismatch')
series = [name for name in (ROOT / 'patches/series').read_text().splitlines()
          if name and not name.startswith('#')]
files = set()
upstream_names = set()
untouched = 0
for name in series:
    for line in (ROOT / 'patches' / name).read_text().splitlines():
        if line.startswith('+++ b/'):
            path = line[6:].split('\t', 1)[0]
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise SystemExit('Unsafe patch path')
            files.add(path)
with tempfile.TemporaryDirectory(prefix='verify-patches-', dir=ROOT / 'work') as staging:
    base = Path(staging)
    wanted = {version + '/' + name: name for name in files}
    with tarfile.open(archive, mode='r|xz') as source:
        for member in source:
            if args.full and (member.isfile() or member.issym()):
                relative = str(Path(member.name).relative_to(version))
                upstream_names.add(relative)
                if relative not in files:
                    actual = ROOT / 'work' / version / relative
                    if member.issym():
                        if not actual.is_symlink() or actual.readlink() != Path(member.linkname):
                            raise SystemExit('Unpatched symlink mismatch: ' + relative)
                    else:
                        expected = hashlib.sha256(source.extractfile(member).read()).hexdigest()
                        if not actual.is_file() or actual.is_symlink() or digest(actual) != expected:
                            raise SystemExit('Unpatched source mismatch: ' + relative)
                    untouched += 1
            name = wanted.get(member.name)
            if name is None or not member.isfile():
                continue
            dst = base / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(source.extractfile(member).read())
    for name in series:
        with (ROOT / 'patches' / name).open('rb') as patch:
            r = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0'], cwd=base,
                               stdin=patch, capture_output=True, text=True)
        if r.returncode or 'offset' in r.stdout or 'fuzz' in r.stdout:
            raise SystemExit(name + ': replay failed or shifted\n' + r.stdout + r.stderr)
    hashes = {}
    for name in sorted(files):
        actual = ROOT / 'work' / version / name
        if (base / name).read_bytes() != actual.read_bytes():
            raise SystemExit('Source mismatch: ' + name)
        hashes[name] = digest(actual)
if args.full:
    tree = ROOT / 'work' / version
    allowed_names = upstream_names | files
    extras = [str(x.relative_to(tree)) for x in tree.rglob('*')
              if (x.is_file() or x.is_symlink()) and str(x.relative_to(tree)) not in allowed_names]
    if extras:
        raise SystemExit('Unrecorded source files: ' + ', '.join(sorted(extras)))
(ROOT / 'work/patch-replay.json').write_text(json.dumps({
    'source_archive_sha256': gcc['sha256'], 'patches_sha256': patch_hashes(ROOT),
    'source_sha256': hashes, 'full_source_verification': args.full,
    'untouched_upstream_files': untouched}, indent=2) + '\n')
print(str(len(series)) + ' patches replay exactly; ' + str(len(files)) + ' source files match.')
if args.full:
    print(str(untouched) + ' additional upstream files match; no unrecorded files.')
