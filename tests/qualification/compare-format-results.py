#!/usr/bin/env python3
"""Compare matching-model formatter logs, allowing equivalent hex notation."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--expected', required=True, type=Path)
p.add_argument('--actual', required=True, type=Path)
p.add_argument('--record', type=Path)
a = p.parse_args()
expected, actual = a.expected.read_text().splitlines(), a.actual.read_text().splitlines()
if len(expected) != len(actual):
    raise SystemExit('Different result lengths: ' + str(len(expected)) + ' vs ' + str(len(actual)))
for index, (left, right) in enumerate(zip(expected, actual), 1):
    if left.startswith('hex|') and right.startswith('hex|'):
        x, y = left.split('|', 2), right.split('|', 2)
        if int(y[1]) == len(y[2]) and float.fromhex(x[2]) == float.fromhex(y[2]):
            continue
    if left != right:
        raise SystemExit('Mismatch on line ' + str(index) + ': ' + repr(left) + ' vs ' + repr(right))
if not actual or actual[-1] != 'format: 0 failures':
    raise SystemExit('Missing successful completion marker')
if a.record:
    a.record.write_text(json.dumps({'lines': len(actual), 'failures': 0,
                                  'hexadecimal_compared_numerically': True}, indent=2) + '\n')
print(str(len(actual)) + ' oracle lines passed.')
