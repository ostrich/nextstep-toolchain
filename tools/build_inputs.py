"""Small shared provenance helpers for compiler experiments."""
import hashlib

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def patch_hashes(root):
    return {name: digest(root / 'patches' / name)
            for name in (root / 'patches/series').read_text().splitlines()
            if name and not name.startswith('#')}
