#!/usr/bin/env python3
"""Archive an audited release stage whose code matches a tested bundle."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def code_digest(path):
    """Ignore ar timestamps/ownership, but compare every member name and byte."""
    data = path.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        return digest(data)
    offset, members = 8, []
    while offset < len(data):
        header = data[offset : offset + 60]
        if len(header) != 60 or header[58:] != b"`\n":
            raise ValueError("Malformed archive: " + str(path))
        size = int(header[48:58])
        content = data[offset + 60 : offset + 60 + size]
        if len(content) != size:
            raise ValueError("Truncated archive: " + str(path))
        members.append((header[:16].decode("ascii"), digest(content)))
        offset += 60 + size + size % 2
    return digest(json.dumps(members).encode())


def core_files(root):
    return {
        str(f.relative_to(root)): code_digest(f)
        for directory in ["bin", "include", "lib", "libexec"]
        for f in (root / directory).rglob("*")
        if f.is_file() and not f.is_symlink() and "__pycache__" not in f.parts
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", type=Path)
    p.add_argument("--tested-bundle", type=Path, required=True)
    p.add_argument("--guest-results", type=Path, required=True)
    p.add_argument("--package-result", type=Path, required=True)
    p.add_argument("--sdk-evidence", type=Path, required=True)
    p.add_argument("--revision", type=int, default=1)
    p.add_argument("--output", type=Path, default=ROOT / "dist")
    a = p.parse_args()
    if a.revision < 1:
        p.error("Revision must be positive")
    stage = a.stage.resolve()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/check-release.py"),
            str(stage),
            "--sdk-evidence",
            str(a.sdk_evidence),
        ],
        check=True,
    )
    expected, actual = core_files(a.tested_bundle), core_files(stage)
    differences = sorted(
        n for n in expected.keys() | actual.keys() if expected.get(n) != actual.get(n)
    )
    if differences:
        p.error("Code differs from tested bundle: " + ", ".join(differences))
    guests = json.loads(a.guest_results.read_text())
    if set(guests) != {"m68k", "i386", "hppa", "sparc"} or any(
        not g.get("passed")
        or not g.get("native_halt")
        or any(code != 0 for code in g.get("fsck", {}).values())
        for g in guests.values()
    ):
        p.error("All four native guest results must pass")
    package = json.loads(a.package_result.read_text())
    if (
        not package.get("passed")
        or not package.get("native_halt")
        or package.get("fsck_exitcode") != 0
    ):
        p.error("Package integration did not pass")
    sdk = json.loads(a.sdk_evidence.read_text())
    if not sdk.get("link_checks_passed"):
        p.error("SDK compilation/link checks did not pass")
    manifest = json.loads((stage / "toolchain.json").read_text())
    version = manifest["gcc_version"]
    name = f"nextstep-toolchain-{version}-{a.revision}-linux-x86_64"
    destination = a.output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / (name + ".tar.gz")
    if archive.exists():
        p.error("Archive already exists; use a fresh output directory")
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    epoch = int(
        subprocess.check_output(
            ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT, text=True
        )
    )
    report = {
        "schema": 1,
        "qualified": True,
        "release_revision": a.revision,
        "source_commit": source_commit,
        "required_host_python": "3.11+",
        "code_fingerprint": digest(json.dumps(actual, sort_keys=True).encode()),
        "archive_comparison": "All code bytes match tested bundle; ar header dates and owners ignored",
        "native_languages": [
            "C",
            "C++ with threads and exceptions",
            "Objective-C",
            "Objective-C++",
        ],
        "native_targets": sorted(guests),
        "package_install_verify_remove": "passed",
        "sdk_four_target_link_checks": "passed",
        "pending": [],
        "scope": "See docs/validation.md for checks and limits",
    }
    (stage / "share/distribution.json").write_text(json.dumps(report, indent=2) + "\n")
    shutil_doc = ROOT / "docs/validation.md"
    (stage / "docs/validation.md").write_bytes(shutil_doc.read_bytes())
    manifest["files"] = {
        str(f.relative_to(stage)): digest(f.read_bytes())
        for f in stage.rglob("*")
        if f.is_file() and not f.is_symlink() and f != stage / "toolchain.json"
    }
    (stage / "toolchain.json").write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/check-release.py"),
            str(stage),
            "--sdk-evidence",
            str(a.sdk_evidence),
        ],
        check=True,
    )
    temporary = archive.with_suffix(".partial")
    try:
        with temporary.open("wb") as raw, gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=epoch
        ) as gz:
            with tarfile.open(fileobj=gz, mode="w|") as tar:
                for f in [stage, *sorted(stage.rglob("*"))]:
                    entry = tar.gettarinfo(
                        str(f),
                        arcname=name
                        + ("/" + str(f.relative_to(stage)) if f != stage else ""),
                    )
                    entry.uid = entry.gid = 0
                    entry.uname = entry.gname = "root"
                    entry.mtime = epoch
                    if entry.isfile():
                        with f.open("rb") as stream:
                            tar.addfile(entry, stream)
                    else:
                        tar.addfile(entry)
        temporary.rename(archive)
    finally:
        temporary.unlink(missing_ok=True)
    archive.with_name(archive.name + ".sha256").write_text(
        digest(archive.read_bytes()) + "  " + archive.name + "\n"
    )
    print(archive)


if __name__ == "__main__":
    main()
