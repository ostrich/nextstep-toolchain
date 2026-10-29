#!/usr/bin/env python3
"""Build a fresh, local portable release stage. Nothing is installed or uploaded."""

import argparse, subprocess, sys, tempfile, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--sdk", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--jobs", type=int, default=4, help="Make jobs per target")
a = p.parse_args()
if any(c.isspace() for c in str(ROOT)):
    p.error(
        "Use a source checkout without whitespace; release output paths may contain spaces"
    )
out = a.output.resolve()
if out.exists():
    p.error("Output must be a new directory")


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)


run(sys.executable, ROOT / "tools/prepare.py", "--patched")
run(sys.executable, ROOT / "tools/verify-patches.py", "--full")
if not (ROOT / "work/release-host-tools/build-record.json").is_file():
    run(
        sys.executable,
        ROOT / "tools/build-host-tools.py",
        "--output",
        ROOT / "work/release-host-tools",
        "--jobs",
        a.jobs,
    )
run(
    sys.executable,
    ROOT / "tools/build-cxx-toolchain.py",
    "--sdk",
    a.sdk.resolve(),
    "--jobs",
    a.jobs,
    "--parallel-targets",
    "4",
)
run("make", "-C", ROOT / "src/nextufs", "WITH_FUSE=0", "-j" + str(a.jobs))
with tempfile.TemporaryDirectory(prefix="release-stage-", dir=ROOT / "work") as staging:
    staging = Path(staging)
    configuration = json.loads((ROOT / "toolchain/cxx-build-set.json").read_text())
    configuration["shared_tools"] = str(staging / "shared-tools")
    build_set = staging / "build-set.json"
    build_set.write_text(json.dumps(configuration))
    run(
        sys.executable,
        ROOT / "tools/build-shared-tools.py",
        "--host-build",
        ROOT / "work/release-host-tools",
        "--output",
        staging / "shared-tools",
    )
    run(
        sys.executable,
        ROOT / "tools/install-toolchain.py",
        "--build-set",
        build_set,
        "--prefix",
        staging / "compiler-input",
    )
    run(
        sys.executable,
        ROOT / "tools/assemble-release.py",
        "--toolchain",
        staging / "compiler-input",
        "--output",
        out,
    )
