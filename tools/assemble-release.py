#!/usr/bin/env python3
"""Assemble a fresh portable release stage from a qualified compiler bundle."""

import argparse, hashlib, json, shutil
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--toolchain", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--shared-tools", type=Path, help="Qualified mkshlib build for this host")
p.add_argument("--nextufs", type=Path, help="nextufs executable built for this host")
p.add_argument(
    "--compiler-builds",
    type=Path,
    default=Path(__file__).resolve().parents[1] / "work/release-compilers",
)
p.add_argument(
    "--host-tools",
    type=Path,
    default=Path(__file__).resolve().parents[1] / "work/release-host-tools",
)
a = p.parse_args()
source = a.toolchain.resolve()
out = a.output.resolve()
if out.exists():
    p.error("Output must be a new directory")
if not (source / "toolchain.json").is_file():
    p.error("Missing compiler build manifest")
shutil.copytree(
    source,
    out,
    symlinks=True,
    ignore=shutil.ignore_patterns("sdk", "workspace", "work", "dist", "__pycache__"),
)
# A portable input may contain wrapped host programs. All such programs must
# be replaced, including mkshlib, before bundling this host's runtime again.
wrapped_input = (out / "share/host-runtime.json").exists()
if wrapped_input:
    if not a.shared_tools or not a.nextufs:
        p.error("Rehosting a portable bundle requires --shared-tools and --nextufs")
    shutil.rmtree(out / "libexec/host")
    (out / "share/host-runtime.json").unlink()
    for elf in (out / "libexec").rglob("*.elf"):
        elf.unlink()
if wrapped_input:
    for arch in ["i386", "m68k", "hppa", "sparc"]:
        for suffix in ["gcc", "g++", "cpp", "as", "ld", "ar", "ranlib", "nm", "strip", "libtool"]:
            (out / "bin" / (arch + "-next-nextstep3.3-" + suffix)).unlink(missing_ok=True)
    (out / "bin/nextstep-lipo").unlink(missing_ok=True)
root = Path(__file__).resolve().parents[1]
import subprocess

source_manifest = json.loads((source / "toolchain.json").read_text())
for arch in ["m68k", "i386", "hppa", "sparc"]:
    build = a.compiler_builds / arch
    record = json.loads((build / "build-record.json").read_text())
    if record.get("patches_sha256") != source_manifest["gcc_patches_sha256"]:
        p.error(
            "Compiler patchset differs from qualified target-runtime bundle: " + arch
        )
    for name in ["xgcc", "cc1", "cc1plus", "cc1obj", "cc1objplus"]:
        binary = build / "gcc" / name
        if (
            hashlib.sha256(binary.read_bytes()).hexdigest()
            != record["compiler_sha256"][name]
        ):
            p.error("Compiler build digest mismatch: " + arch + "/" + name)
        dest = out / "libexec/gcc" / arch / name
        shutil.copy2(binary, dest)
        subprocess.run(["strip", "--strip-unneeded", str(dest)], check=True)
host_record = json.loads((a.host_tools / "build-record.json").read_text())
if host_record["sources"] != json.loads((root / "toolchain/sources.json").read_text()):
    p.error("Host-tool source pins differ")
expected_patches = {
    name: hashlib.sha256((root / "toolchain/patches" / name).read_bytes()).hexdigest()
    for name in (root / "toolchain/patches/series").read_text().splitlines()
    if name and not name.startswith("#")
}
if host_record["patches_sha256"] != expected_patches:
    p.error("Host-tool patchset differs")
for name, digest in host_record["compatibility_sha256"].items():
    if (
        hashlib.sha256((root / "toolchain/compat" / name).read_bytes()).hexdigest()
        != digest
    ):
        p.error("Host compatibility source differs: " + name)
if host_record.get("status") != "passed":
    p.error("Host tool build did not pass")
for name in [
    "as-i386",
    "as-m68k",
    "as-hppa",
    "as-sparc",
    "ld",
    "lipo",
    "libtool",
    "nm",
    "ar",
    "strip",
]:
    binary = a.host_tools / "bin" / name
    if (
        hashlib.sha256(binary.read_bytes()).hexdigest()
        != host_record["binaries_sha256"][name]
    ):
        p.error("Host tool build digest mismatch: " + name)
    dest = out / "libexec/cctools" / name
    shutil.copy2(binary, dest)
    subprocess.run(["strip", "--strip-unneeded", str(dest)], check=True)

if a.shared_tools:
    shared_record = json.loads((a.shared_tools / "build-record.json").read_text())
    binary = a.shared_tools / "bin/mkshlib"
    if (shared_record.get("status") != "passed" or
            hashlib.sha256(binary.read_bytes()).hexdigest() != shared_record["mkshlib_sha256"] or
            shared_record["host_build_record_sha256"] != hashlib.sha256((a.host_tools / "build-record.json").read_bytes()).hexdigest()):
        p.error("Shared-tool provenance mismatch")
    shutil.copy2(binary, out / "libexec/cctools/mkshlib")
    subprocess.run(["strip", "--strip-unneeded", str(out / "libexec/cctools/mkshlib")], check=True)
shutil.copy2(source / "toolchain.json", out / "share/compiler-input.json")
shutil.copy2(root / "tools/nextstep-gcc", out / "bin/nextstep-gcc")
shutil.copy2(root / "tools/nextstep-shlib", out / "bin/nextstep-shlib")
shutil.copytree(
    root / "src/nextpkg",
    out / "libexec/nextpkg",
    dirs_exist_ok=True,
    ignore=shutil.ignore_patterns("__pycache__", "tests"),
)
(out / "bin/nextpkg").write_text(
    '#!/bin/sh\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1\nexec python3 -B "$base/libexec/nextpkg/nextpkg.py" "$@"\n'
)
(out / "bin/nextpkg").chmod(0o755)
(out / "README.md").write_text(
    (root / "docs/bundle-README.md")
    .read_text()
    .replace("@GCC_VERSION@", source_manifest["gcc_version"])
    .replace("@HOST_ARCH@", {"aarch64": "arm64"}.get(__import__("platform").machine(), __import__("platform").machine()))
)
shutil.copy2(root / "PORTING.md", out / "PORTING.md")
shutil.copytree(root / "licenses", out / "share/licenses", dirs_exist_ok=True)
shutil.copy2(root / "src/nextufs/LICENSE", out / "share/licenses/nextufs-MIT.txt")
shutil.copy2(root / "src/nextpkg/LICENSE", out / "share/licenses/nextpkg-MIT.txt")
(out / "README.txt").unlink(missing_ok=True)
shutil.copy2(root / "tools/setup-sdk.py", out / "libexec/setup-sdk.py")
(out / "libexec/nextufs").mkdir(exist_ok=True)
shutil.copy2(a.nextufs or root / "src/nextufs/nextufs", out / "libexec/nextufs/nextufs")
subprocess.run(
    ["strip", "--strip-unneeded", str(out / "libexec/nextufs/nextufs")], check=True
)
(out / "bin/setup-sdk").write_text(
    '#!/bin/sh\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1\nexec python3 -B "$base/libexec/setup-sdk.py" "$@"\n'
)
(out / "bin/setup-sdk").chmod(0o755)
for name in ["sdk", "workspace", "examples", "docs"]:
    (out / name).mkdir(exist_ok=True)
shutil.copytree(root / "examples", out / "examples", dirs_exist_ok=True)
shutil.copy2(root / "docs/user-shared-libraries.md", out / "docs/shared-libraries.md")
shutil.copy2(root / "docs/user-packaging.md", out / "docs/packaging.md")
record = {
    "schema": 1,
    "qualified": False,
    "compiler_manifest_sha256": hashlib.sha256(
        (source / "toolchain.json").read_bytes()
    ).hexdigest(),
    "required_host_python": "3.11+",
    "pending": [
        "SDK setup",
        "private host dependencies",
        "relocation and native qualification",
    ],
}
(out / "share").mkdir(exist_ok=True)
record["distribution_files"] = {
    str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in [out / "bin/nextstep-gcc", out / "bin/nextpkg"]
}
(out / "share/distribution.json").write_text(json.dumps(record, indent=2) + "\n")
import subprocess

subprocess.run(
    [
        __import__("sys").executable,
        str(root / "tools/bundle-host-runtime.py"),
        str(out),
    ],
    check=True,
)
subprocess.run(
    [
        __import__("sys").executable,
        str(root / "tools/install-public-tools.py"),
        str(out),
    ],
    check=True,
)
manifest = json.loads((out / "toolchain.json").read_text())
manifest["host_tools_build_record_sha256"] = hashlib.sha256(
    (a.host_tools / "build-record.json").read_bytes()
).hexdigest()
manifest["release_host_compilers"] = {
    arch: hashlib.sha256(
        (a.compiler_builds / arch / "build-record.json").read_bytes()
    ).hexdigest()
    for arch in ["m68k", "i386", "hppa", "sparc"]
}
import platform
manifest["host_architecture"] = platform.machine()
manifest["files"] = {
    str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in out.rglob("*")
    if f.is_file() and not f.is_symlink() and f.name != "toolchain.json"
}
(out / "toolchain.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
