#!/usr/bin/env python3
"""Reject stale patch ledgers and edited source before certifying a GCC build."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_inputs import patch_hashes, source_files, verify_source

class PreparedSourceTests(unittest.TestCase):
    def test_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'patches').mkdir()
            (root / 'patches/series').write_text('one.patch\n')
            patch = root / 'patches/one.patch'
            patch.write_text('patch bytes\n')
            (root / 'sources.lock.json').write_text(json.dumps({'gcc': {'sha256': 'locked'}}))
            source = root / 'source'
            source.mkdir()
            unit = source / 'unit.c'
            unit.write_text('original\n')
            link = source / 'link'
            link.symlink_to('unit.c')
            with self.assertRaises(SystemExit):
                verify_source(root, source)
            manifest = source / '.prepared-source.json'
            manifest.write_text(json.dumps({'source_archive_sha256': 'locked',
                'patches_sha256': patch_hashes(root), 'files': source_files(source)}))
            self.assertEqual(len(verify_source(root, source)), 64)
            unit.write_text('changed\n')
            with self.assertRaises(SystemExit):
                verify_source(root, source)
            unit.write_text('original\n')
            link.unlink()
            link.symlink_to('other.c')
            with self.assertRaises(SystemExit):
                verify_source(root, source)
            link.unlink()
            link.symlink_to('unit.c')
            patch.write_text('new patch\n')
            with self.assertRaises(SystemExit):
                verify_source(root, source)

if __name__ == '__main__':
    unittest.main()
