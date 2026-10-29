#!/usr/bin/env python3
"""Add conventional target-prefixed commands to a fresh release bundle."""

import argparse
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("bundle", type=Path)
root = p.parse_args().bundle.resolve()


def command(name, target, flags=""):
    path = root / "bin" / name
    if path.exists() or path.is_symlink():
        raise SystemExit("Refusing to replace " + str(path))
    path.write_text(
        '#!/bin/sh\nroot=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1\nexec "$root/'
        + target
        + '" '
        + flags
        + ' "$@"\n'
    )
    path.chmod(0o755)


for arch in ["m68k", "i386", "hppa", "sparc"]:
    prefix = arch + "-next-nextstep3.3-"
    command(prefix + "gcc", "bin/nextstep-gcc", "-arch " + arch)
    command(prefix + "g++", "bin/nextstep-g++", "-arch " + arch)
    command(prefix + "cpp", "bin/nextstep-gcc", "-arch " + arch + " -E")
    command(prefix + "as", "libexec/cctools/as-" + arch, "-arch " + arch)
    command(prefix + "ld", "libexec/cctools/ld", "-arch " + arch)
    for name in ["ar", "ranlib", "nm", "strip", "libtool"]:
        command(prefix + name, "libexec/cctools/" + name)
command("nextstep-lipo", "libexec/cctools/lipo")
