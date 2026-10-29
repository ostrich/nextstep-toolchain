"""Package user-supplied documentation without product-specific rewriting."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nextpkg.compress import decompress
from nextpkg.manifest import load, UserError
from nextpkg.package import build, check


class ReadmeTests(unittest.TestCase):
    def test_supplied_readme_preserved_in_archive_and_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prose = b'Example\r\n\r\n  Keep this spacing.\r\nLatin-1: caf\xe9\r\n'
            (root / 'README.txt').write_bytes(prose)
            (root / 'data').write_bytes(b'unchanged payload')
            spec = {'name': 'Example', 'version': '1.0', 'revision': 1,
                    'readme': str(root / 'README.txt'),
                    'files': {'usr/local/share/example/data': {'source': str(root / 'data')}}}
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps(spec))
            with contextlib.redirect_stdout(io.StringIO()):
                archive = build(manifest, root / 'output')
                check(archive)
            with tarfile.open(archive) as tar:
                outer = tar.extractfile('README.txt').read()
                raw = io.BytesIO()
                decompress(tar.extractfile('Example.pkg/Example.tar.Z'), raw)
            with tarfile.open(fileobj=io.BytesIO(raw.getvalue())) as tar:
                installed = tar.extractfile('./usr/local/share/doc/Example/README.txt').read()
            self.assertEqual(outer, prose)
            self.assertEqual(installed, prose)

    def test_readme_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'manifest.json'
            manifest.write_text(json.dumps({'name': 'Example', 'version': '1.0',
                                           'readme_profile': 'nextports', 'files': {}}))
            with self.assertRaisesRegex(UserError, 'Unknown manifest field.*readme_profile'):
                load(manifest)
