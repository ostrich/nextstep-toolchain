#!/usr/bin/env python3
"""Check an authorized package with native tools in an isolated agent guest.

Only creates a unique temporary directory; does not install files or receipts.
Full GUI installation, architecture thinning and removal are separate checks.
"""

import argparse
import hashlib
from pathlib import Path
import runpy
import shutil
import sys
import tarfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nextpkg.package import check, read_members
from nextpkg.compress import decompress
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("archive", type=Path)
p.add_argument("--socket", required=True, type=Path)
p.add_argument("--agent-client", required=True, type=Path)
p.add_argument("--records", required=True, type=Path)
p.add_argument("--arch", default="i386", choices=["i386", "m68k", "hppa", "sparc"])
a = p.parse_args()
check(a.archive)
a.records.mkdir(parents=True, exist_ok=True)
name, members = read_members(a.archive)
try:
    (a.records / "package.bom").write_bytes(members[name + ".bom"])
    with (a.records / "payload.Z").open("wb") as out:
        shutil.copyfileobj(members[name + ".tar.Z"], out)
finally:
    for value in members.values():
        if hasattr(value, "close"):
            value.close()
A = runpy.run_path(str(a.agent_client.resolve()))["GuestAgent"]
d = "/private/tmp/nextpkg-native-" + str(time.time_ns())
with A(str(a.socket.resolve()), 30) as guest:

    def run(command):
        result = guest.execute(
            "/bin/sh", ["-c", "set -e; umask 022; " + command], execution_timeout=60
        )
        with (a.records / "native.log").open("ab") as log:
            log.write(result["stdout"] + result["stderr"])
        if result.get("exitcode") != 0:
            raise RuntimeError("Native command failed; inspect native.log")

    run("/bin/mkdir " + d)
    guest.upload(a.records / "package.bom", d + "/package.bom")
    guest.upload(a.records / "payload.Z", d + "/payload.Z")
    run(
        "/usr/etc/lsbom -arch "
        + a.arch
        + " "
        + d
        + "/package.bom > "
        + d
        + "/lsbom.txt 2>"
        + d
        + "/lsbom.err"
    )
    for f in ("lsbom.txt", "lsbom.err"):
        guest.download(d + "/" + f, a.records / f)
    if (
        not (a.records / "lsbom.txt").stat().st_size
        or (a.records / "lsbom.err").stat().st_size
    ):
        raise RuntimeError("Native lsbom rejected or warned about the BOM")
    run("/usr/ucb/zcat " + d + "/payload.Z > " + d + "/payload.tar")
    run(
        "/bin/mkdir "
        + d
        + "/proof && cd "
        + d
        + "/proof && /NextAdmin/Installer.app/installer_tar xf ../payload.tar"
    )
    run("cd " + d + "/proof && /bin/tar cf ../proof.tar .")
    guest.download(d + "/proof.tar", a.records / "proof.tar")
with tempfile.TemporaryFile() as raw, (a.records / "payload.Z").open(
    "rb"
) as compressed:
    decompress(compressed, raw)
    raw.seek(0)
    with tarfile.open(fileobj=raw) as original, tarfile.open(
        a.records / "proof.tar"
    ) as proof:
        expected = {m.name.removeprefix("./").rstrip("/") or ".": m for m in original}
        actual = {m.name.removeprefix("./").rstrip("/") or ".": m for m in proof}
        if set(expected) != set(actual):
            raise RuntimeError("Native extraction changed the path inventory")
        for path, m in expected.items():
            got = actual[path]
            if (m.uid, m.gid) != (got.uid, got.gid):
                raise RuntimeError("Ownership differs: " + path)
            # Native extraction clears setuid/setgid. The GUI post-install hook
            # is responsible for restoring them, as separately tested.
            if (m.mode & ~0o6000) != (got.mode & ~0o6000):
                raise RuntimeError("Permissions differ: " + path)
            if m.isfile() or m.islnk():
                if not (got.isfile() or got.islnk()):
                    raise RuntimeError("File type differs: " + path)
                if (
                    hashlib.file_digest(original.extractfile(m), "sha256").digest()
                    != hashlib.file_digest(proof.extractfile(got), "sha256").digest()
                ):
                    raise RuntimeError("File bytes differ: " + path)
            elif m.issym():
                if not got.issym() or m.linkname != got.linkname:
                    raise RuntimeError("Symlink differs: " + path)
            elif not got.isdir():
                raise RuntimeError("Directory differs: " + path)
print("PASS native BOM listing and Installer payload extraction:", name)
print("Records:", a.records)
