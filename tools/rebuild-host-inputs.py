#!/usr/bin/env python3
"""Rebuild optimized host compiler frontends and Mach-O tools for a release."""

import argparse, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--jobs", type=int, default=4, help="Make jobs per compiler target")
a = p.parse_args()
if a.jobs < 1:
    p.error("Jobs must be positive")
logs = ROOT / "work/release-input-logs"
logs.mkdir(parents=True, exist_ok=True)


def run(label, args):
    with (logs / (label + ".log")).open("wb") as output:
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / args[0]), *args[1:]],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print("Built " + label, flush=True)


run("prepare", ["prepare.py", "--patched"])


def compiler(arch):
    run(
        arch,
        [
            "build.py",
            "--arch",
            arch,
            "--languages",
            "c,c++,objc,obj-c++",
            "--thread-model",
            "nextstep",
            "--exception-model",
            "sjlj",
            "--jobs",
            str(a.jobs),
            "--output",
            str(ROOT / "work/release-compilers" / arch),
        ],
    )


with ThreadPoolExecutor(max_workers=5) as pool:
    futures = [
        pool.submit(compiler, arch) for arch in ["m68k", "i386", "hppa", "sparc"]
    ]
    futures.append(
        pool.submit(
            run,
            "cctools",
            [
                "build-host-tools.py",
                "--jobs",
                str(a.jobs),
                "--output",
                str(ROOT / "work/release-host-tools"),
            ],
        )
    )
    for future in futures:
        future.result()
