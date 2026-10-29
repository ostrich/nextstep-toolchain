#!/usr/bin/env python3
"""Update only NextStepCompat inside an existing compiler bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolchain', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--backup', type=Path, required=True, help='New directory for replaced files and original manifest')
    a = p.parse_args()
    tc, build, backup = (x.resolve() for x in (a.toolchain, a.build, a.backup))
    if (ROOT.parent / 'install/snapshots').resolve() in tc.parents:
        p.error('Installed snapshots are immutable; copy current to a staging directory first')
    if backup.exists() or backup == tc or tc in backup.parents:
        p.error('Backup must be a new directory outside the installed bundle')
    record = json.loads((build / 'build-record.json').read_text())
    if record.get('canonical_shared'):
        p.error('Shared-runtime intermediates cannot replace the static compiler component')
    manifest = json.loads((tc / 'toolchain.json').read_text())
    if record.get('status') != 'passed' or not manifest.get('nextstepcompat'):
        p.error('Require a successful component build and an integrated compiler bundle')
    source_hashes = {str(f.relative_to(ROOT)): digest(f) for f in sorted(ROOT.rglob('*'))
                     if f.is_file() and '__pycache__' not in f.parts and
                     f.relative_to(ROOT).parts[0] != 'tests'}
    for name, expected in source_hashes.items():
        if (name.endswith(('.c', '.h', '.patch', '.json')) or name == 'build.py') and record['sources_sha256'].get(name) != expected:
            p.error('Source differs from component build: ' + name)
    updates = {Path('include/nextstepcompat') / f.relative_to(ROOT / 'include'): f
               for f in sorted((ROOT / 'include').rglob('*')) if f.is_file()}
    for arch in manifest['targets']:
        library = build / arch / 'libnextstepcompat.a'
        if digest(library) != record['targets'][arch]['archive_sha256']:
            p.error('Component archive checksum mismatch: ' + arch)
        updates[Path('lib') / arch / 'libnextstepcompat.a'] = library
    replaced = {name for name in manifest['files'] if name.startswith('include/nextstepcompat/') or
                name.endswith('/libnextstepcompat.a')}
    # Verify the whole installed bundle before touching it, and prove that
    # unrelated compiler/runtime files retain their recorded bytes afterward.
    for name, expected in manifest['files'].items():
        if digest(tc / name) != expected:
            p.error('Installed bundle checksum mismatch: ' + name)
    backup.mkdir(parents=True)
    shutil.copy2(tc / 'toolchain.json', backup / 'toolchain.json')
    for name in replaced:
        destination = backup / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tc / name, destination)
    for name in replaced:
        if Path(name) not in updates:
            (tc / name).unlink()
            del manifest['files'][name]
    for destination, source in updates.items():
        target = tc / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.nextstepcompat-update')
        shutil.copy2(source, temporary)
        temporary.replace(target)
        manifest['files'][str(destination)] = digest(source)
    manifest['nextstepcompat'].update(version=record['version'], sources_sha256=source_hashes,
                                    build_record_sha256=digest(build / 'build-record.json'))
    for name, expected in manifest['files'].items():
        if digest(tc / name) != expected:
            raise SystemExit('Post-install integrity check failed: ' + name)
    temporary = tc / 'toolchain.json.nextstepcompat-update'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(tc / 'toolchain.json')
    print('Updated NextStepCompat only:', tc)


if __name__ == '__main__':
    main()
