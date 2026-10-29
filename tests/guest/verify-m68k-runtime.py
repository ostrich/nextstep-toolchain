#!/usr/bin/env python3
"""Validate a collected native 3.3 transcript against the prepared m68k probes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_inputs import digest
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--transcript', type=Path, required=True, help='collect after native halt')
p.add_argument('--output', type=Path, default=ROOT / 'work/abi-m68k/runtime-results.json')
args = p.parse_args()
text = args.transcript.read_text()
if not text.startswith('Modern GCC NEXTSTEP 3.3 runtime probes\n') or '\nCOMPLETE\n' not in text:
    raise SystemExit('Missing batch identity/completion marker')
expected = {}
for level in ['O1', 'O2', 'O3', 'Os']:
    directory = ROOT / 'work/abi-m68k' / level
    expected['mixed-' + level] = ('mixed ABI: 32 checks, 0 failures', directory / 'mixed33', directory / 'results.json')
for name, output in [('objc33', 'objc runtime: 52 checks, 0 failures'),
                      ('objcxx33', 'objc runtime: 52 checks, 0 failures'),
                      ('strings33', 'objc constants: passed'),
                      ('stringsxx33', 'objc constants: passed'),
                      ('cxx33', 'cxx probe: 1 42\ncxx destructor: 42')]:
    directory = ROOT / 'work/languages-m68k'
    expected[name] = (output, directory / name, directory / 'results.json')
actual = {}
name = None
lines = []
for line in text.split('\nCOMPLETE\n', 1)[0].splitlines():
    if line.startswith('TEST: ./'):
        if name is not None:
            raise SystemExit('Missing status for ' + name)
        name = line[len('TEST: ./'):]
        if name in actual:
            raise SystemExit('Duplicate test ' + name)
        lines = []
    elif line.startswith('STATUS: '):
        if name is None:
            raise SystemExit('Status outside a test')
        actual[name] = {'status': int(line[8:]), 'stdout': '\n'.join(lines)}
        name = None
    elif name is not None:
        lines.append(line)
if name is not None or actual.keys() != expected.keys():
    raise SystemExit('Incomplete or unexpected test set')
results = {'target_os': 'NEXTSTEP 3.3', 'target_cpu': 'm68k',
           'transcript_sha256': digest(args.transcript), 'tests': []}
for name, (output, binary, record) in expected.items():
    row = actual[name]
    row.update({'name': name, 'passed': row['status'] == 0 and row['stdout'] == output,
                'binary_sha256': digest(binary), 'build_record_sha256': digest(record)})
    results['tests'].append(row)
    print(name + ': ' + ('PASS' if row['passed'] else 'FAIL'))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(results, indent=2) + '\n')
if not all(row['passed'] for row in results['tests']):
    raise SystemExit(1)
