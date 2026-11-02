"""Small shared provenance helpers for compiler experiments."""
import hashlib

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def patch_hashes(root):
    return {name: digest(root / 'patches' / name)
            for name in (root / 'patches/series').read_text().splitlines()
            if name and not name.startswith('#')}


def source_files(source):
    """Hash source bytes and symlink targets, independent of timestamps."""
    return {str(p.relative_to(source)): ('link:' + str(p.readlink())
            if p.is_symlink() else digest(p))
            for p in sorted(source.rglob('*'))
            if (p.is_file() or p.is_symlink())
            and p.name != '.prepared-source.json'}

def verify_source(root, source):
    import json
    manifest = source / '.prepared-source.json'
    if not manifest.exists():
        raise SystemExit('Uncertified GCC source; prepare a fresh tree with tools/prepare.py --patched.')
    record = json.loads(manifest.read_text())
    locked = json.loads((root / 'sources.lock.json').read_text())['gcc']
    if record['source_archive_sha256'] != locked['sha256'] or record['patches_sha256'] != patch_hashes(root):
        raise SystemExit('Prepared GCC source does not match the locked source and maintained patches.')
    if record['files'] != source_files(source):
        raise SystemExit('Prepared GCC source changed since extraction; refusing inaccurate build provenance.')
    return digest(manifest)
