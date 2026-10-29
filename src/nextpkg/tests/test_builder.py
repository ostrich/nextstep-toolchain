"""Host regression tests for native formats, validation and reproducibility."""

import io
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nextpkg.bom import Builder, Store, FormatError
from nextpkg.compress import compress, decompress
from nextpkg.manifest import load, UserError
from nextpkg.package import build, check
from nextpkg.payload import checksum


class Compression(unittest.TestCase):
    def test_dictionary_widths_and_clear(self):
        rng = random.Random(716)
        for data in (
            b"",
            b"a",
            bytes(range(256)),
            b"abcd" * 100000,
            rng.randbytes(700000),
        ):
            encoded = io.BytesIO()
            compress(io.BytesIO(data), encoded)
            decoded = io.BytesIO()
            decompress(io.BytesIO(encoded.getvalue()), decoded)
            self.assertEqual(decoded.getvalue(), data)
            result = subprocess.run(
                ["gzip", "-dc"], input=encoded.getvalue(), capture_output=True
            )
            self.assertEqual((result.returncode, result.stdout), (0, data))

    def test_output_bound(self):
        encoded = io.BytesIO()
        compress(io.BytesIO(b"x" * 10000), encoded)
        with self.assertRaisesRegex(ValueError, "size limit"):
            decompress(io.BytesIO(encoded.getvalue()), io.BytesIO(), limit=100)

    def test_invalid_code(self):
        with self.assertRaises(ValueError):
            decompress(io.BytesIO(b"\x1f\x9d\x90\xff\x01"), io.BytesIO())


class BillOfMaterials(unittest.TestCase):
    def test_three_level_tree_and_index_growth(self):
        rows = [
            (str(i).zfill(5).encode() + b"x" * 75, b"value" * 4) for i in range(60000)
        ]
        b = Builder()
        for i in range(1, 10):
            b.tree(i, rows if i == 3 else [])
        data = b.finish()
        s = Store(data)
        self.assertEqual(s.tree(3), rows)
        self.assertGreater(s.index + 16 + s.count * 8, 8192)
        self.assertGreaterEqual(struct.unpack_from(">I", s.block(3), 8)[0], 2)

    def test_cycles_fail_closed(self):
        b = Builder()
        for i in range(1, 10):
            b.tree(i, [])
        data = bytearray(b.finish())
        pointer = struct.unpack_from(">I", data, 0x810 + 3 * 8)[0] & ~8191
        struct.pack_into(">I", data, pointer + 8, 1)
        struct.pack_into(">I", data, pointer + 28, 3 << 13)
        with self.assertRaisesRegex(FormatError, "Cycle"):
            Store(data).tree(3)

    def test_native_checksum_vectors(self):
        for data, expected in (
            (b"", 0),
            (b"a", 97),
            (b"abc", 6513249),
            (b"123456789", 2627707557),
            (bytes(range(256)), 2682265664),
            (b"hello\n", 3570522998),
        ):
            self.assertEqual(checksum(io.BytesIO(data)), expected)


class Packages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "tool").write_text("#!/bin/sh\necho hello\n")
        (self.root / "README.txt").write_text("A test package.\n")
        self.spec = {
            "name": "Example",
            "version": "1.2",
            "revision": 3,
            "readme": "README.txt",
            "files": {
                "bin/tool": {"source": "tool", "mode": "4755"},
                "bin/link": {"link": "tool"},
                "bin/hard": {"hardlink": "bin/tool", "mode": "4755"},
            },
        }
        self.path = self.root / "package.json"

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(self.spec))

    def test_build_check_reproducible_modes_links_and_hooks(self):
        self.write()
        out = build(self.path, self.root / "out", progress=lambda _: None)
        first = out.read_bytes()
        result = check(out)
        self.assertEqual(result["version"], "1.2-3")
        with tarfile.open(out) as t:
            hook = t.extractfile("Example.pkg/Example.post_install").read()
            self.assertIn(b"chmod 4755", hook)
            self.assertEqual(
                t.getmember("Example.pkg/Example.post_install").mode, 0o755
            )
            for m in t:
                self.assertEqual((m.uid, m.gid, m.mtime), (0, 0, 0))
        with self.assertRaisesRegex(UserError, "already exists"):
            build(self.path, self.root / "out", progress=lambda _: None)
        build(self.path, self.root / "out", force=True, progress=lambda _: None)
        self.assertEqual(out.read_bytes(), first)

    def test_invalid_paths_and_modes(self):
        for path in (
            "../bad",
            "/bin/bad",
            "dir/../bad",
            "dir//bad",
            "./bad",
            "bad\nname",
            "x" * 98,
        ):
            self.spec["files"] = {path: {"source": "tool"}}
            self.write()
            with self.assertRaises(UserError):
                load(self.path)
        self.spec["files"] = {"bin/tool": {"source": "tool", "mode": "rwx"}}
        self.write()
        with self.assertRaisesRegex(UserError, "octal"):
            load(self.path)

    def test_parent_symlink_and_bad_hardlink(self):
        for files in (
            {"bin": {"link": "elsewhere"}, "bin/tool": {"source": "tool"}},
            {"alias": {"hardlink": "missing"}},
        ):
            self.spec["files"] = files
            self.write()
            with self.assertRaises(UserError):
                load(self.path)

    def test_source_symlink_not_followed(self):
        (self.root / "alias").symlink_to("tool")
        self.spec["files"] = {"tool": {"source": "alias"}}
        self.write()
        with self.assertRaisesRegex(UserError, "not a symlink"):
            load(self.path)

    def test_dry_run_has_no_output(self):
        self.write()
        out = self.root / "out"
        self.assertIsNone(build(self.path, out, dry_run=True, progress=lambda _: None))
        self.assertFalse(out.exists())

    def test_checker_rejects_payload_corruption(self):
        self.write()
        archive = build(self.path, self.root / "out", progress=lambda _: None)
        broken = self.root / "broken.pkg"
        broken.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar:
                if member.isfile() and member.name.startswith("Example.pkg/"):
                    (
                        broken
                        / Path(member.name).name.replace("Example.", "broken.", 1)
                    ).write_bytes(tar.extractfile(member).read())
        # Alter a regular-file checksum while leaving a structurally valid BOM.
        from nextpkg.bom import u32

        bom = bytearray((broken / "broken.bom").read_bytes())
        store = Store(bom)
        base = u32(bom, store.index + 16 + 3 * 8) & ~8191
        node = store.block(3)[16:]
        for i in range(struct.unpack_from(">H", node, 18)[0]):
            offset = struct.unpack_from(">H", node, 20 + 2 * i)[0]
            descriptor, length = struct.unpack_from(">HH", node, offset)
            keylen = (descriptor >> 1) & 8191
            if node[offset + 4 : offset + 4 + keylen].endswith(b"tool"):
                position = base + 16 + offset + 4 + keylen + 18
                bom[position] ^= 1
                break
        else:
            self.fail("Missing tool BOM entry")
        (broken / "broken.bom").write_bytes(bom)
        with self.assertRaisesRegex(UserError, "checksum differs"):
            check(broken)

    def test_composed_hooks_are_self_contained(self):
        (self.root / "remove.sh").write_text('#!/bin/sh\necho removed > "$2/marker"\n')
        self.spec["provides"] = ["libexample.1.dylib"]
        self.spec["hooks"] = {"pre_delete": "remove.sh"}
        self.write()
        archive = build(self.path, self.root / "out", progress=lambda _: None)
        with tarfile.open(archive) as tar:
            hook = tar.extractfile("Example.pkg/Example.pre_delete").read()
            payload = io.BytesIO()
            decompress(io.BytesIO(tar.extractfile("Example.pkg/Example.tar.Z").read()), payload)
            with tarfile.open(fileobj=io.BytesIO(payload.getvalue())) as contents:
                names = [m.name.removeprefix("./") for m in contents]
                self.assertIn("usr/local/share/nextports/consumers/Example.deps", names)
                self.assertFalse(any("openstep-libs" in name for name in names))
            self.assertIn(b"/usr/local/share/nextports/consumers/*.deps", hook)
            self.assertIn(b"/usr/local/share/openstep-libs/consumers/*.deps", hook)
            self.assertNotIn(b"pre_delete.user", hook)
            self.assertIn(b" -c ", hook)
            self.assertLess(hook.index(b"fgrep"), hook.index(b" -c "))
            self.assertFalse(any(m.name.endswith(".user") for m in tar))


    def test_non_string_architecture_has_useful_error(self):
        self.spec["architectures"] = [{}]
        self.write()
        with self.assertRaisesRegex(UserError, "architectures"):
            load(self.path)

    def test_cli_reports_invalid_json_without_traceback(self):
        self.path.write_text('{"name":')
        cli = Path(__file__).resolve().parents[1] / "nextpkg.py"
        result = subprocess.run(
            [sys.executable, str(cli), "build", str(self.path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("nextpkg:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_manifest_key(self):
        self.path.write_text('{"name":"Example","name":"Other"}')
        with self.assertRaisesRegex(UserError, "Duplicate manifest key"):
            load(self.path)

    def test_staging_directory_preserves_links_and_modes(self):
        stage = self.root / "stage"
        stage.mkdir()
        (stage / "tool").write_text("#!/bin/sh\necho staged\n")
        (stage / "tool").chmod(0o755)
        os.link(stage / "tool", stage / "alias")
        (stage / "link").symlink_to("tool")
        self.spec.pop("files")
        self.spec["root"] = "stage"
        self.write()
        spec, entries = load(self.path)
        self.assertEqual(sum(e.kind == "hardlink" for e in entries), 1)
        self.assertTrue(all((e.uid, e.gid) == (0, 0) for e in entries))
        archive = build(self.path, self.root / "out", progress=lambda _: None)
        self.assertEqual(check(archive)["version"], "1.2-3")

    def test_java_magic_is_not_a_macho_binary(self):
        (self.root / "tool").write_bytes(b"\xca\xfe\xba\xbe\0\0\0\x34\0\1" + b"\0" * 12)
        self.spec["files"] = {"share/Test.class": {"source": "tool"}}
        self.write()
        archive = build(self.path, self.root / "out", progress=lambda _: None)
        self.assertTrue(archive.name.endswith(".pkg.tar.gz"))
        check(archive)

    def test_binary_hook_contributes_architecture(self):
        (self.root / "hook").write_bytes(
            struct.pack("<7I", 0xFEEDFACE, 7, 3, 2, 0, 0, 0)
        )
        self.spec["hooks"] = {"pre_delete": "hook"}
        self.write()
        archive = build(self.path, self.root / "out", progress=lambda _: None)
        self.assertTrue(archive.name.endswith(".pkg.I.tar.gz"))
        with tarfile.open(archive) as tar:
            store = Store(tar.extractfile("Example.pkg/Example.bom").read())
            metadata = dict(store.tree(5))[b"BOM Archs Info"]
            self.assertIn(struct.pack(">iiII", 7, 3, 0, 0), metadata)

    def test_unknown_field(self):
        self.spec["revison"] = 3
        self.write()
        with self.assertRaisesRegex(UserError, "revison"):
            load(self.path)

    def test_architecture_mismatch(self):
        # Minimal thin Intel Mach-O. Advertising it for SPARC must fail.
        (self.root / "tool").write_bytes(
            struct.pack("<7I", 0xFEEDFACE, 7, 3, 2, 0, 0, 0)
        )
        self.spec["files"] = {"bin/tool": {"source": "tool", "mode": "0755"}}
        self.spec["architectures"] = ["i386", "sparc"]
        self.write()
        with self.assertRaisesRegex(UserError, "lacks an advertised"):
            build(self.path, self.root / "out", progress=lambda _: None)

    def test_fixed_vm_library_requires_execute_permission(self):
        for endian, cpu in [("<", 7), (">", 6)]:
            thin = struct.pack(endian + "7I", 0xFEEDFACE, cpu, 0, 3, 0, 0, 0)
            fat = struct.pack(">IIiiIII", 0xCAFEBABE, 1, cpu, 0, 28, len(thin), 2) + thin
            for data in [thin, fat]:
                with self.subTest(endian=endian, fat=data is fat):
                    destination = self.root / f"out-{cpu}-{len(data)}"
                    (self.root / "library").write_bytes(data)
                    self.spec["files"] = {"lib/example.shlib": {"source": "library", "mode": "0644"}}
                    self.write()
                    with self.assertRaisesRegex(ValueError, "requires execute permission"):
                        build(self.path, destination, progress=lambda _: None)
                    self.spec["files"]["lib/example.shlib"]["mode"] = "0755"
                    self.write()
                    # Check scans the packaged image as well as its BOM modes.
                    archive = build(self.path, destination, progress=lambda _: None)
                    check(archive)


if __name__ == "__main__":
    unittest.main()
