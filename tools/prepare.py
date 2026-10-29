#!/usr/bin/env python3
"""Fetch a hash-locked GCC release; never overwrite an existing source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patched', action='store_true', help='prepare the experimental target tree')
    args = parser.parse_args()
    gcc = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']
    downloads = ROOT / 'work/downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / gcc['url'].rsplit('/', 1)[1]
    if not archive.exists():
        temporary = archive.with_suffix(archive.suffix + '.part')
        with urllib.request.urlopen(gcc['url']) as response, temporary.open('wb') as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        temporary.replace(archive)
    hashes = {name: hashlib.new(name) for name in ('sha256', 'sha512')}
    with archive.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            for digest in hashes.values():
                digest.update(chunk)
    for name, digest in hashes.items():
        if digest.hexdigest() != gcc[name]:
            raise SystemExit(f'{archive.name}: {name} mismatch; refusing extraction')
    parent = ROOT / 'work' if args.patched else ROOT / 'work/pristine'
    parent.mkdir(parents=True, exist_ok=True)
    source = parent / ('gcc-' + gcc['version'])
    print(f'{archive.name}: both locked hashes match', flush=True)
    if source.exists():
        print('Source already exists; left untouched (not certified pristine).')
    else:
        with tempfile.TemporaryDirectory(prefix='extract-', dir=parent) as staging:
            subprocess.run(['tar', '-xJf', str(archive), '-C', staging], check=True)
            extracted = Path(staging) / source.name
            print('Extracted verified official release without patches.', flush=True)
            if args.patched:
                for name in (ROOT / 'patches/series').read_text().splitlines():
                    if name and not name.startswith('#'):
                        with (ROOT / 'patches' / name).open('rb') as patch:
                            subprocess.run(['patch', '-p1', '--batch', '--forward', '--fuzz=0'],
                                           cwd=extracted, stdin=patch, check=True)
                print('Applied ordered target patches.', flush=True)
            extracted.rename(source)

if __name__ == '__main__':
    main()
