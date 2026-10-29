#!/usr/bin/env python3
"""Extract a private NEXTSTEP developer SDK without mounting the CD."""

import argparse, hashlib, json, os, shutil, stat, struct, subprocess, tempfile, sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("media", type=Path)
    p.add_argument("--nextufs", type=Path, default=ROOT / "libexec/nextufs/nextufs")
    p.add_argument("--compiler", type=Path, default=ROOT / "bin/nextstep-gcc")
    p.add_argument("--output", type=Path, default=ROOT / "sdk/nextstep3.3")
    p.add_argument("--skip-link-checks", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args()
    media = a.media.resolve()
    out = a.output.resolve()
    ufs = a.nextufs.resolve()
    if out.exists():
        p.error("SDK already exists; choose a new output directory")
    out.parent.mkdir(parents=True, exist_ok=True)

    def listing(path):
        return json.loads(
            subprocess.check_output(
                [str(ufs), "browse", "--json-follow", str(media), path]
            )
        )

    def raw(path):
        return subprocess.check_output([str(ufs), "browse", "--raw", str(media), path])

    with tempfile.TemporaryDirectory(prefix=".sdk-", dir=out.parent) as temp:
        stage = Path(temp)
        records = {}
        count = [0]

        def extract(source, destination, ancestors=()):
            rows = listing(source)
            node = rows[0]
            key = node["inode"]
            count[0] += 1
            if count[0] > 20000:
                raise ValueError("SDK file count exceeds safety limit")
            if stat.S_ISDIR(node["mode"]):
                if key in ancestors:
                    raise ValueError("SDK symlink cycle at " + source)
                destination.mkdir(parents=True, exist_ok=True)
                for row in rows[1:]:
                    name = row["name"]
                    if name in [".", ".."] or "/" in name or not name:
                        raise ValueError("Unsafe CD filename")
                    if name.startswith("."):
                        continue
                    extract(source + "/" + name, destination / name, ancestors + (key,))
            elif stat.S_ISREG(node["mode"]):
                data = raw(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                destination.chmod(0o644)
                records[str(destination.relative_to(stage))] = hashlib.sha256(
                    data
                ).hexdigest()
                if len(records) % 250 == 0:
                    print("Extracted " + str(len(records)) + " files", flush=True)
            else:
                raise ValueError("Unsupported SDK object: " + source)

        for source, target in [
            ("/usr/include", "usr/include"),
            ("/lib", "lib"),
            ("/usr/lib", "usr/lib"),
        ]:
            print("Extracting " + source, flush=True)
            extract(source, stage / target)
        for required in ["usr/include/ansi/stdio.h", "lib/crt0.o", "lib/libsys_s.a"]:
            if not (stage / required).is_file():
                raise ValueError("Developer SDK missing " + required)
        with media.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if not a.skip_link_checks:
            with tempfile.TemporaryDirectory(prefix="sdk-test-") as check_dir:
                check = Path(check_dir)
                (check / "hello.c").write_text(
                    '#include <stdio.h>\nint main(void){puts("SDK check");return 0;}\n'
                )
                for arch in ["m68k", "i386", "hppa", "sparc"]:
                    print("Checking " + arch + " compile and link", flush=True)
                    subprocess.run(
                        [
                            str(a.compiler.resolve()),
                            "--sdk",
                            str(stage),
                            "-O2",
                            "-arch",
                            arch,
                            str(check / "hello.c"),
                            "-o",
                            str(check / arch),
                        ],
                        check=True,
                    )
        (stage / "sdk.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "media_sha256": digest,
                    "link_checks_passed": not a.skip_link_checks,
                    "targets": ["m68k", "i386", "hppa", "sparc"],
                    "files": records,
                },
                indent=2,
            )
            + "\n"
        )
        os.rename(stage, out)
    print("SDK extracted to " + str(out))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("setup-sdk: " + str(error), file=sys.stderr)
        raise SystemExit(1)
