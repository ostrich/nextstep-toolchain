#!/usr/bin/env python3
"""Exercise GCC build-system queries through the installed public driver."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--driver', type=Path, help='Uninstalled driver candidate to test')
p.add_argument('--sdk', type=Path, help='Also check dependency-only preprocessing')
a = p.parse_args()
tc = a.toolchain.resolve()
version = json.loads((tc / 'toolchain.json').read_text())['gcc_version']
for arch in ['i386', 'm68k', 'hppa', 'sparc']:
    base = [str((a.driver or tc / 'bin/nextstep-gcc').resolve()), '-arch', arch]
    for flags in [['-dumpversion'], ['-dumpfullversion'],
                  ['-dumpversion', '-dumpfullversion'],
                  ['-dumpfullversion', '-dumpversion']]:
        assert subprocess.check_output(base + flags, text=True).strip() == version
    specs = subprocess.check_output(base + ['-dumpspecs'], text=True)
    assert '*libgcc:' in specs
    result = subprocess.run(base + ['-dumpmachine', '-dumpversion'], capture_output=True)
    assert result.returncode != 0
    print(arch + ': version, combined version, specs and query rejection passed')

    if a.sdk:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'query-source.c'
            source.write_text('#include <stdio.h>\nint query_source;\n')
            for flag in ['-M', '-MM']:
                output = subprocess.check_output(base + ['--sdk', str(a.sdk.resolve()),
                                                        flag, str(source)], text=True)
                assert 'query-source.o:' in output
                assert 'query-source.c' in output
            assert not source.with_suffix('.o').exists()
        print(arch + ': dependency-only preprocessing passed')
