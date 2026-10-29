#!/usr/bin/env python3
"""Audit a fresh binary release stage before archiving it."""

import argparse, hashlib, json, re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("bundle", type=Path)
p.add_argument("--sdk-evidence", type=Path)
a = p.parse_args()
root = a.bundle.resolve()
manifest = json.loads((root / "toolchain.json").read_text())
actual_files = {
    str(f.relative_to(root))
    for f in root.rglob("*")
    if f.is_file() and not f.is_symlink() and f != root / "toolchain.json"
}
actual_links = {str(f.relative_to(root)) for f in root.rglob("*") if f.is_symlink()}
if actual_files != set(manifest["files"]) or actual_links != set(manifest["symlinks"]):
    raise SystemExit("Release contents differ from manifest")
for name, digest in manifest["files"].items():
    f = root / name
    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
        raise SystemExit("Release file changed: " + name)
for name, target in manifest["symlinks"].items():
    f = root / name
    if (
        not f.is_symlink()
        or str(f.readlink()) != target
        or not f.resolve().is_relative_to(root)
    ):
        raise SystemExit("Invalid release symlink: " + name)
for name in ["sdk", "workspace"]:
    if list((root / name).iterdir()):
        raise SystemExit("User-owned directory must be empty: " + name)
known_sdk = {}
if a.sdk_evidence:
    sdk = json.loads(a.sdk_evidence.read_text())
    known_sdk = {digest: name for name, digest in sdk["files"].items()}
# Check path shapes rather than names of a particular developer or workspace.
private_path = re.compile(rb"/(?:home|Users)/[^/\x00\r\n\t '\"<>]+/|/run/media/[^/\x00\r\n\t '\"<>]+/")
count = 0
for f in root.rglob("*"):
    if not f.is_file() or f.is_symlink():
        continue
    data = f.read_bytes()
    count += 1
    if str(Path.home()).encode() in data or private_path.search(data):
        raise SystemExit("Private build detail in " + str(f.relative_to(root)))
    if f.suffix in [".iso", ".raw", ".img", ".pyc"]:
        raise SystemExit("Unwanted build/media file: " + str(f.relative_to(root)))
    digest = hashlib.sha256(data).hexdigest()
    if len(data) > 256 and digest in known_sdk:
        raise SystemExit("Original SDK file in release: " + known_sdk[digest])
print(
    "PASS:", count, "files; hashes, symlinks, private paths and SDK exclusion checked"
)
