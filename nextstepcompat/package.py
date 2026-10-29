#!/usr/bin/env python3
"""Package an independently built NIHS NextStepCompat runtime and SDK."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--shared", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--toolchain", type=Path, default=ROOT.parent / "install/current")
p.add_argument("--revision", type=int, default=6)
a = p.parse_args()
shared = a.shared.resolve()
out = a.output.resolve()
tc = a.toolchain.resolve()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


record = json.loads((shared / "build-record.json").read_text())
constructor = json.loads((shared / "shared-build.json").read_text())
spec = json.loads((ROOT / "shared.json").read_text())
if a.revision < 1:
    p.error("Revision must be positive")
if record["status"] != "passed" or constructor["spec_sha256"] != digest(
    ROOT / "shared.json"
):
    p.error("Require a successful shared build with the current ABI specification")
for name, expected in record["artifacts_sha256"].items():
    if digest(shared / name) != expected:
        p.error("Shared artifact changed: " + name)
info = subprocess.check_output(
    [
        str(tc / "libexec/cctools/lipo"),
        "-info",
        str(shared / "libnextstepcompat.1.shlib"),
    ],
    text=True,
)
if any(n not in info.split() for n in ["m68k", "i386", "hppa", "sparc"]):
    p.error("Missing NIHS runtime slice")
out.mkdir(parents=True, exist_ok=False)
(out / "archives").mkdir()
version = (ROOT / "VERSION").read_text().strip()
runtime = []
development = []
for name, dev in [("NextStepCompat", False), ("NextStepCompat-dev", True)]:
    d = out / name
    d.mkdir()
    files = {}

    def add(target, source, mode="0644"):
        files[target] = {"source": str(source), "mode": mode}

    if dev:
        add("usr/local/lib/libnextstepcompat.a", shared / "libnextstepcompat.a")
        for header in sorted((ROOT / "include").rglob("*.h")):
            add(
                "usr/local/include/nextstepcompat/"
                + str(header.relative_to(ROOT / "include")),
                header,
            )
        description = "C and POSIX compatibility headers and NIHS shared import library for NEXTSTEP development."
        paragraphs = [
            name + " " + version + "-" + str(a.revision),
            description,
            "Install the matching NextStepCompat runtime first. The .a file imports the separately installed shared runtime; it contains no static implementation.",
            "Headers install in /usr/local/include/nextstepcompat and the import library in /usr/local/lib. With nextstep-gcc, select this wrapper directory using --compat-headers rather than a second -I wrapper tree. Link with -lnextstepcompat. The Linux toolchain ships its own matching development inputs.",
        ]
        dependencies = ["libnextstepcompat.1.shlib"]
        provides = []
    else:
        add(
            "usr/local/lib/libnextstepcompat.1.shlib",
            shared / "libnextstepcompat.1.shlib",
            "0755",
        )
        description = "Shared C and POSIX compatibility runtime for modern NEXTSTEP and OPENSTEP applications."
        paragraphs = [
            name + " " + version + "-" + str(a.revision),
            description,
            "Supports NEXTSTEP 3.3 on NeXT 68k, Intel, HPPA and SPARC, plus Intel OPENSTEP 4.2. Install before applications that require it. This package does not replace the system C library.",
            "The runtime installs in /usr/local/lib and supplements missing or incompatible C/POSIX interfaces, including formatting, strings, process and signal handling, time and locale support. Applications select the required shared interface when linked. Compatible updates preserve the public function-entry layout; restart dependent programs after updates.",
        ]
        dependencies = []
        provides = ["libnextstepcompat.1.shlib"]
    paragraphs.append(
        "Managed pthread support includes thread lifecycle, TLS destructors, cleanup handlers, deferred cancellation, typed/robust mutexes, timed conditions and locks, rwlocks, barriers, spinlocks and fork handlers. It is not full POSIX threads: native libc blocking calls are not cancellation points; custom stacks, realtime policies, per-thread Unix signals and process-shared locks are unsupported."
    )
    for license in sorted(ROOT.rglob("*")):
        if license.is_file() and license.name in [
            "LICENSE",
            "COPYRIGHT",
            "TRE-LICENSE.txt",
        ]:
            add(
                "usr/local/share/licenses/"
                + name
                + "/"
                + str(license.relative_to(ROOT)).replace("/", "-"),
                license,
            )
    public = d / "BUILD.json"
    public.write_text(
        json.dumps(
            {
                "version": version,
                "revision": a.revision,
                "shared_minor": spec["minor_version"],
                "shared_producer_sha256": digest(shared / "build-record.json"),
                "shared_constructor_sha256": digest(shared / "shared-build.json"),
                "spec_sha256": digest(ROOT / "shared.json"),
                "artifacts_sha256": record["artifacts_sha256"],
            },
            indent=2,
        )
        + "\n"
    )
    add("usr/local/share/build-info/" + name + ".json", public)
    readme = d / "README.txt"
    readme.write_text(
        "\n\n".join(
            textwrap.fill(t, 76, break_long_words=False, break_on_hyphens=False)
            for t in paragraphs
        )
        + "\n"
    )
    manifest = d / "package.json"
    manifest.write_text(
        json.dumps(
            {
                "name": name,
                "version": version,
                "revision": a.revision,
                "title": name,
                "description": description,
                "architectures": ["m68k", "i386", "hppa", "sparc"],
                "readme": str(readme),
                "files": files,
                "dependencies": dependencies,
                "provides": provides,
            },
            indent=2,
        )
        + "\n"
    )
    cmd = [sys.executable, str(PROJECT / "src/nextpkg/nextpkg.py")]
    subprocess.run(
        cmd + ["build", str(manifest), "--output", str(out / "archives")], check=True
    )
    archive = (
        out / "archives" / ("%s-%s-%d.pkg.NIHS.tar.gz" % (name, version, a.revision))
    )
    subprocess.run(cmd + ["check", str(archive)], check=True)
    entry = {
        "name": name,
        "version": version,
        "revision": a.revision,
        "archive": archive.name,
        "sha256": digest(archive),
        "dependencies": dependencies,
        "provides": provides,
    }
    (development if dev else runtime).append(entry)
(out / "runtime-packages.json").write_text(json.dumps(runtime, indent=2) + "\n")
(out / "development-packages.json").write_text(json.dumps(development, indent=2) + "\n")
print(
    "Built independent runtime/development packages; installed qualification is separate"
)
