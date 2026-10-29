#!/usr/bin/env python3
"""Verify a staged bundle and atomically select the canonical installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def series(directory):
    return {name: digest(directory / name) for name in
            (directory / 'series').read_text().splitlines()
            if name and not name.startswith('#')}
def verify(bundle):
    manifest = json.loads((bundle / 'toolchain.json').read_text())
    for field, directory in [('gcc_patches_sha256', ROOT / 'patches'),
                             ('host_tools_patches_sha256', ROOT / 'toolchain/patches')]:
        if manifest[field] != series(directory):
            raise ValueError('Bundle does not match maintained patches: ' + field)
    if manifest['host_tools'] != json.loads((ROOT / 'toolchain/sources.json').read_text()):
        raise ValueError('Bundle uses different cctools source pins')
    for name, expected in manifest['host_compatibility_sha256'].items():
        if digest(ROOT / 'toolchain/compat' / name) != expected:
            raise ValueError('Host portability source changed: ' + name)
    def compatibility_inputs(items):
        return {name: value for name, value in items.items()
                if not name.startswith('tests/') and
                Path(name).suffix in ('.c', '.h', '.patch', '.json')}
    current = {str(path.relative_to(ROOT / 'nextstepcompat')): digest(path)
               for path in (ROOT / 'nextstepcompat').rglob('*') if path.is_file()}
    if compatibility_inputs(current) != compatibility_inputs(
            manifest['nextstepcompat']['sources_sha256']):
        raise ValueError('NextStepCompat source inputs changed after bundle build')
    if 'fixed_vm_tools' in manifest:
        fixed = manifest['fixed_vm_tools']
        if (fixed['sources'] != json.loads((ROOT / 'toolchain/fixed-vm/sources.json').read_text())
                or fixed['patches_sha256'] != series(ROOT / 'toolchain/fixed-vm/patches')):
            raise ValueError('Shared-library constructor provenance mismatch')
        if fixed.get('wrappers_sha256') != {name: digest(ROOT / 'tools' / name) for name in ['nextstep-gcc', 'nextstep-shlib']}:
            raise ValueError('Shared-library wrapper sources changed after staging')
    for name, expected in manifest['files'].items():
        path = bundle / name
        if not path.resolve().is_relative_to(bundle.resolve()) or digest(path) != expected:
            raise ValueError('Bundle file mismatch: ' + name)
    for name, target in manifest['symlinks'].items():
        if not (bundle / name).is_symlink() or os.readlink(bundle / name) != target:
            raise ValueError('Bundle symlink mismatch: ' + name)
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--check', action='store_true', help='Verify without promoting')
    a = p.parse_args()
    source = a.bundle.resolve()
    manifest = verify(source)
    identity = digest(source / 'toolchain.json')
    if a.check:
        print('Verified ' + identity)
        return
    install = ROOT / 'install'
    snapshots = install / 'snapshots'
    snapshots.mkdir(parents=True, exist_ok=True)
    destination = snapshots / identity
    if not destination.exists():
        temporary = Path(tempfile.mkdtemp(prefix='.stage-', dir=snapshots))
        try:
            shutil.copytree(source, temporary, symlinks=True, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            verify(temporary)
            subprocess.run([str(temporary / 'bin/nextstep-gcc'), '--version'], check=True,
                           stdout=subprocess.DEVNULL)
            temporary.rename(destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    verify(destination)
    link = install / '.current-new'
    link.unlink(missing_ok=True)
    link.symlink_to(destination.relative_to(install))
    link.replace(install / 'current')
    print('Selected install/current: ' + identity)
if __name__ == '__main__':
    main()
