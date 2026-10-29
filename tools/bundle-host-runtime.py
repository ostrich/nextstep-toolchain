#!/usr/bin/env python3
"""Give trusted, locally built ELF tools private loaders and shared libraries."""

import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("bundle", type=Path)
a = p.parse_args()
root = a.bundle.resolve()
records = []
# Inspect the original set before creating any private files.
if (root / "share/host-runtime.json").exists():
    p.error("Host runtimes are already bundled; assemble into a fresh output directory")
programs = []
for f in root.rglob("*"):
    if not f.is_file() or f.is_symlink() or not os.access(f, os.X_OK):
        continue
    with f.open("rb") as stream:
        header = stream.read(5)
    if header[:4] == b"\x7fELF":
        programs.append((f, header[4]))
for f, bits in programs:
    info = subprocess.check_output(["readelf", "-l", str(f)], text=True)
    match = re.search(r"Requesting program interpreter: ([^\]]+)\]", info)
    if not match:
        continue
    loader = Path(match[1])
    directory = root / "libexec/host" / ("elf32" if bits == 1 else "elf64")
    directory.mkdir(parents=True, exist_ok=True)
    deps = subprocess.check_output(["ldd", str(f)], text=True)
    if "not found" in deps:
        raise RuntimeError("Missing build-host dependency: " + str(f))
    paths = {
        loader,
        *[Path(x) for x in re.findall(r"(?:=>\s+|^\s*)(/[^\s]+)", deps, re.M)],
    }
    for source in paths:
        dest = directory / source.name
        data = source.read_bytes()
        if dest.exists() and dest.read_bytes() != data:
            raise RuntimeError("Conflicting host library " + source.name)
        if not dest.exists():
            shutil.copy2(source, dest)
    real = f.with_name(f.name + ".elf")
    if real.exists():
        raise RuntimeError("Already wrapped: " + str(f))
    f.rename(real)
    relative = real.relative_to(root)
    back = os.path.relpath(root, f.parent)
    f.write_text(
        '#!/bin/sh\nroot=$(CDPATH= cd -- "$(dirname -- "$0")/'
        + back
        + '" && pwd) || exit 1\nNEXTSTEP_HOST_EXECUTABLE="$root/'
        + str(relative)
        + '"; export NEXTSTEP_HOST_EXECUTABLE\nexec "$root/'
        + str(directory.relative_to(root) / loader.name)
        + '" --argv0 "$0" --library-path "$root/'
        + str(directory.relative_to(root))
        + '" "$root/'
        + str(relative)
        + '" "$@"\n'
    )
    f.chmod(0o755)
    records.append(
        {
            "program": str(f.relative_to(root)),
            "loader": str((directory / loader.name).relative_to(root)),
            "libraries": sorted({s.name for s in paths}),
        }
    )
packages = []
# Package metadata is optional build evidence, never a runtime dependency.
for name in ["glibc", "lib32-glibc", "gmp", "mpfr", "libmpc", "libisl", "zstd"]:
    for desc in Path("/var/lib/pacman/local").glob(name + "-*/desc"):
        sections = desc.read_text().split("\n\n")
        fields = {
            row.splitlines()[0].strip("%"): row.splitlines()[1:]
            for row in sections
            if row.startswith("%")
        }
        if fields.get("NAME") == [name]:
            packages.append(
                {
                    key.lower(): fields.get(key, [])
                    for key in ["NAME", "VERSION", "URL", "LICENSE"]
                }
            )
runtime_files = {
    str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in (root / "libexec/host").rglob("*")
    if f.is_file()
}
(root / "share/host-runtime.json").write_text(
    json.dumps(
        {
            "schema": 1,
            "programs": records,
            "runtime_files": runtime_files,
            "build_packages": packages,
        },
        indent=2,
    )
    + "\n"
)
print("Wrapped", len(records), "host programs")
