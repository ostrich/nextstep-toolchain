#!/usr/bin/env python3
"""Compare RISC method encodings with output from original NEXTSTEP GCC 2.5.8.

The checked-in expectations are metadata strings, not copied SDK/source files.
Assembly acceptance and runtime forwarding are separate checks.
"""
import argparse
import json
from pathlib import Path
import sys
import re
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest, patch_hashes

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['sparc', 'hppa'], required=True)
args = p.parse_args()
build = ROOT / 'work' / ('build-' + args.arch) / 'gcc'
out = ROOT / 'work' / ('argument-layout-' + args.arch)
out.mkdir(parents=True, exist_ok=True)
fixture = ROOT / 'tests/objc-argument-layout.m'
expected = json.loads((ROOT / 'tests/objc-argument-layout.json').read_text())[args.arch]
records = []
for language, frontend in [('objective-c', 'cc1obj'), ('objective-c++', 'cc1objplus')]:
    assembly = out / (language + '.s')
    command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2',
               '-x' + language, '-fno-exceptions', '-fno-rtti', '-S',
               str(fixture), '-o', str(assembly)]
    r = subprocess.run(command, capture_output=True, text=True)
    actual = sorted(set(re.findall(r'\.ascii\s+"(i\d[^"\\]*)', assembly.read_text()))) if not r.returncode else []
    passed = r.returncode == 0 and actual == expected
    records.append({'language': language, 'command': command, 'exitcode': r.returncode,
                    'stderr': r.stderr, 'expected': expected, 'actual': actual,
                    'passed': passed, 'compiler_sha256': digest(build / frontend)})
    print(language + ': ' + ('PASS' if passed else 'FAIL'))
(out / 'results.json').write_text(json.dumps({'patches_sha256': patch_hashes(ROOT),
    'fixture_sha256': digest(fixture), 'tests': records}, indent=2) + '\n')
if not all(r['passed'] for r in records):
    raise SystemExit(1)
