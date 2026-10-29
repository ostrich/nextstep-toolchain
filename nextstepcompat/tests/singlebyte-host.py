#!/usr/bin/env python3
"""Run the 16-bit-wide single-byte contract under host sanitizers."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
headers = out / 'include'
headers.mkdir(exist_ok=True)
prefix = out / 'host-prefix.h'
names = set()
for name in ['wchar.h', 'wctype.h']:
    names.update(re.findall(r'\b([A-Za-z]\w*)\([^;{}]*\);',
                            (ROOT / 'include' / name).read_text()))
# Do not interpose 16-bit-wide test functions into the host's 32-bit-wide libc.
prefix.write_text(''.join('#define ' + n + ' ns33_test_' + n + '\n'
                          for n in sorted(names)))
for name in ['ns33-multibyte.h', 'wchar.h', 'wctype.h']:
    shutil.copyfile(ROOT / 'include' / name, headers / name)
command = ['cc', '-O2', '-g', '-std=gnu17', '-fshort-wchar', '-fno-builtin',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-include', str(prefix), '-I' + str(headers),
           *[str(ROOT / 'src' / name) for name in
             ['multibyte.c', 'wide-string.c', 'wide-ctype.c']],
           str(ROOT / 'tests/singlebyte.c'), '-o', str(out / 'test')]
result = subprocess.run(command, capture_output=True, text=True)
(out / 'build.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit('Host build failed: ' + str(out / 'build.log'))
result = subprocess.run([str(out / 'test')], capture_output=True, text=True)
(out / 'results.log').write_text(result.stdout + result.stderr)
(out / 'results.json').write_text(json.dumps({
    'command': command, 'exitcode': result.returncode,
    'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
print(result.stdout + result.stderr, end='')
raise SystemExit(result.returncode)
