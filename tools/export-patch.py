#!/usr/bin/env python3
"""Export a development stage against its frozen predecessor patches."""
import argparse
import hashlib
import difflib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', type=int, choices=[4, 5, 6, 7], default=7)
args = parser.parse_args()
gcc = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']
version = 'gcc-' + gcc['version']
files = ['gcc/config.gcc', 'gcc/config/i386/nextstep.h', 'gcc/config/i386/i386.cc',
         'gcc/config/nextstep-protos.h', 'gcc/config/nextstep.cc',
         'gcc/config/nextstep-c.cc', 'gcc/config/t-nextstep',
         'gcc/objc/objc-next-runtime-abi-01.cc', 'gcc/objc/objc-encoding.cc', 'gcc/objc/objc-runtime-shared-support.cc', 'gcc/objc/objc-act.cc',
         'libcpp/directives.cc', 'libcpp/include/cpplib.h', 'libcpp/files.cc',
         'gcc/c-family/c-target.def', 'gcc/c-family/c-lex.cc',
         'gcc/doc/tm.texi.in', 'gcc/doc/tm.texi']
previous = ['0001-i386-add-experimental-nextstep-c-target.patch',
            '0002-nextstep-restore-header-and-language-support.patch',
            '0003-nextstep-add-other-architectures.patch']
output_name = '0004-nextstep-restore-sparc-and-hppa.patch'
files += ['gcc/config/nextstep.h', 'gcc/config/m68k/nextstep.h',
          'gcc/config/m68k/m68k.cc', 'gcc/config/sparc/nextstep.h',
          'gcc/config/sparc/sparc.cc', 'gcc/config/pa/nextstep.h',
          'gcc/config/pa/pa.cc', 'gcc/config/pa/pa.h',
          'gcc/config/pa/pa.md', 'gcc/config/pa/predicates.md']
if args.stage >= 5:
    previous.append(output_name)
    output_name = '0005-nextstep-add-cxx-runtime-support.patch'
    files += ['gcc/target.def', 'gcc/builtins.cc',
              'libstdc++-v3/src/filesystem/ops.cc', 'libstdc++-v3/src/c++17/fs_ops.cc',
              'libstdc++-v3/include/c_global/cstdio', 'libstdc++-v3/include/bits/basic_string.h',
              'libatomic/configure.tgt', 'libatomic/config/nextstep/lock.c',
              'libatomic/config/nextstep/host-config.h', 'libatomic/configure.ac', 'libatomic/configure',
              'libgcc/config/pa/sync-libfuncs.c', 'config/gthr.m4', 'gcc/configure.ac', 'gcc/configure', 'libgcc/configure',
              'libgcc/gthr-nextstep.h', 'libstdc++-v3/crossconfig.m4', 'libstdc++-v3/configure', 'libstdc++-v3/libsupc++/tinfo.cc',
              'libstdc++-v3/configure.host', 'libstdc++-v3/config/os/nextstep/os_defines.h',
              'libstdc++-v3/config/os/nextstep/ctype_base.h',
              'libstdc++-v3/config/os/nextstep/ctype_inline.h',
              'libstdc++-v3/config/os/nextstep/ctype_configure_char.cc',
              'libstdc++-v3/src/c++23/std.cc.in', 'libstdc++-v3/src/c++23/std-clib.cc.in',
              'libstdc++-v3/config.h.in', 'libstdc++-v3/config/locale/generic/c_locale.h',
              'libstdc++-v3/src/c++17/floating_to_chars.cc',
              'libstdc++-v3/include/bits/locale_facets.tcc']
if args.stage >= 6:
    previous.append(output_name)
    output_name = '0006-hppa-preserve-exact-ldil-constants.patch'
if args.stage >= 7:
    previous.append(output_name)
    output_name = '0007-m68k-align-nextstep-local-stack-frames.patch'
if len(files) != len(set(files)):
    raise SystemExit('Duplicate patch export source path')
archive_path = ROOT / 'work/downloads' / (version + '.tar.xz')
with archive_path.open('rb') as stream:
    if hashlib.file_digest(stream, 'sha256').hexdigest() != gcc['sha256']:
        raise SystemExit('Release archive hash mismatch')
with tempfile.TemporaryDirectory(prefix='patch-base-', dir=ROOT / 'work') as staging:
    base = Path(staging)
    # Read the compressed release once, rather than seeking backwards and
    # repeatedly decompressing it for source files in a different order.
    wanted = {version + '/' + name: name for name in files}
    with tarfile.open(archive_path, mode='r|xz') as archive:
        for member in archive:
            name = wanted.get(member.name)
            if name is None or not member.isfile():
                continue
            dst = base / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(archive.extractfile(member).read())
    for name in previous:
        with (ROOT / 'patches' / name).open('rb') as patch:
            subprocess.run(['patch', '-p1', '--batch', '--fuzz=0'], cwd=base,
                           stdin=patch, stdout=subprocess.DEVNULL, check=True)
    output = []
    for name in files:
        old = (base / name).read_text() if (base / name).exists() else ''
        new = (ROOT / 'work' / version / name).read_text()
        output.extend(difflib.unified_diff(io.StringIO(old).readlines(),
                       io.StringIO(new).readlines(),
                       fromfile='a/' + name if old else '/dev/null', tofile='b/' + name))
    (ROOT / 'patches' / output_name).write_text(''.join(output))
(ROOT / 'patches/series').write_text('\n'.join(previous + [output_name]) + '\n')
print(output_name)
