#!/usr/bin/env python3
"""Release archive comparison must ignore metadata, never member contents."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).resolve().parents[1] / "tools/create-release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def archive(content, timestamp):
    header = f"{'test.o/':<16}{timestamp:<12}{0:<6}{0:<6}{'100644':<8}{len(content):<10}`\n".encode()
    return b"!<arch>\n" + header + content + (b"\n" if len(content) % 2 else b"")


class ArchiveTest(unittest.TestCase):
    def test_metadata_is_ignored_but_code_is_not(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "a", Path(temp) / "b"
            a.write_bytes(archive(b"abc", 1))
            b.write_bytes(archive(b"abc", 2))
            self.assertEqual(release.code_digest(a), release.code_digest(b))
            b.write_bytes(archive(b"abd", 2))
            self.assertNotEqual(release.code_digest(a), release.code_digest(b))

    def test_truncated_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            a = Path(temp) / "a"
            a.write_bytes(archive(b"abcd", 1)[:-2])
            with self.assertRaises(ValueError):
                release.code_digest(a)


if __name__ == "__main__":
    unittest.main()
