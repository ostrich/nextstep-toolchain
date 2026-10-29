#!/usr/bin/env python3
"""Create and inspect native NEXTSTEP/OPENSTEP Installer packages on the host."""

import argparse
import json
from pathlib import Path
import sys
import struct
import shlex
import tarfile
from nextpkg import __version__
from nextpkg.manifest import UserError
from nextpkg.package import build, check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="nextpkg " + __version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "init", help="create a ready-to-edit manifest for a staging directory"
    )
    init.add_argument("manifest", type=Path)
    init.add_argument("--name", required=True)
    init.add_argument("--version", required=True)
    init.add_argument(
        "--root", type=Path, required=True, help="payload staging directory"
    )
    make = commands.add_parser("build", help="create a .pkg.tar.gz and SHA256 sidecar")
    make.add_argument("manifest", type=Path)
    make.add_argument("-o", "--output", type=Path, default=Path("dist"))
    make.add_argument(
        "--force", action="store_true", help="replace an existing distribution archive"
    )
    make.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs without writing a package",
    )
    for command in ("check", "inspect"):
        sub = commands.add_parser(
            command,
            help="validate a package and "
            + ("report success" if command == "check" else "show its metadata"),
        )
        sub.add_argument(
            "package", type=Path, help=".pkg directory or distribution archive"
        )
        sub.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args()
    try:
        if args.command == "init":
            if args.manifest.exists():
                raise UserError("Manifest already exists: " + str(args.manifest))
            import os

            spec = {
                "name": args.name,
                "version": args.version,
                "revision": 1,
                "title": args.name,
                "description": "",
                "root": os.path.relpath(
                    args.root.resolve(), args.manifest.resolve().parent
                ),
                "architectures": "auto",
            }
            args.manifest.write_text(json.dumps(spec, indent=2) + "\n")
            print("Created " + str(args.manifest))
            print("Edit the title and description, then run:")
            command = ["python3", sys.argv[0], "build", str(args.manifest)]
            if sys.platform == "win32":
                import subprocess

                rendered = subprocess.list2cmdline(command)
            else:
                rendered = shlex.join(command)
            print("  " + rendered)
        elif args.command == "build":
            build(args.manifest, args.output, args.force, args.dry_run)
        else:
            result = check(args.package)
            if args.json:
                print(json.dumps(result, indent=2))
            elif args.command == "check":
                print(
                    f'PASS {result["name"]} {result["version"]}: {result["entries"]} payload entries agree with the BOM'
                )
            else:
                print(f'{result["name"]} {result["version"]}')
                for key in ("Title", "Description", "DefaultLocation", "Relocatable"):
                    print(f'  {key}: {result["info"].get(key, "") }')
                print(f'  Payload entries: {result["entries"]}')
    except KeyboardInterrupt:
        print("nextpkg: cancelled", file=sys.stderr)
        return 130
    except (
        UserError,
        ValueError,
        OSError,
        KeyError,
        EOFError,
        OverflowError,
        struct.error,
        tarfile.TarError,
        UnicodeError,
    ) as error:
        print("nextpkg: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
