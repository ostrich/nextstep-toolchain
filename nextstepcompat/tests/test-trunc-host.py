#!/usr/bin/env python3
"""Compare the binary64 implementation against host libm on deterministic inputs."""
import argparse
import ctypes
import ctypes.util
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
with tempfile.TemporaryDirectory(prefix='nextstep-trunc-') as temporary:
    library = Path(temporary) / 'trunc.so'
    subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                    '-Dtrunc=ns33_test_trunc', str(ROOT / 'src/trunc.c'), '-o', str(library)], check=True)
    candidate = ctypes.CDLL(str(library)).ns33_test_trunc
    reference = ctypes.CDLL(ctypes.util.find_library('m')).trunc
    for function in [candidate, reference]:
        function.argtypes = [ctypes.c_double]; function.restype = ctypes.c_double
    rng = random.Random(0x4e533333)
    for i in range(1000000):
        bits = rng.getrandbits(64)
        # Quiet NaNs before the call so FP loads cannot vary their payload.
        if bits & 0x7ff0000000000000 == 0x7ff0000000000000 and bits & 0xfffffffffffff:
            bits |= 0x8000000000000
        value = struct.unpack('=d', struct.pack('=Q', bits))[0]
        actual = struct.pack('=d', candidate(value))
        expected = struct.pack('=d', reference(value))
        assert actual == expected, (hex(bits), actual.hex(), expected.hex())
(a.output / 'results.json').write_text(json.dumps({'checks': 1000000, 'failures': 0,
    'oracle': 'host libm trunc', 'seed': '0x4e533333'}, indent=2) + '\n')
print('PASS trunc: 1000000 host libm comparisons')
