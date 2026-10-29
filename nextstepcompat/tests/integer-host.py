#!/usr/bin/env python3
"""Differentially check conversions against host libc and emit guest vectors."""
import argparse
import ctypes
import json
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--check-ilp32', action='store_true', help='Also compare 32-bit long with the host multilib libc')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['cc', '-O2', '-std=gnu11', '-shared', '-fPIC',
    '-Dstrtoll=nextstep_strtoll', '-Dstrtoull=nextstep_strtoull',
    '-Datoll=nextstep_atoll', str(ROOT / 'src/integer-conversion.c'),
    '-o', str(out / 'conversion.so')], check=True)
host = ctypes.CDLL(None, use_errno=True)
port = ctypes.CDLL(str(out / 'conversion.so'), use_errno=True)
def call(lib, name, data, base):
    function = getattr(lib, name)
    function.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int]
    function.restype = (ctypes.c_ulonglong if 'strtoull' in name else
                       ctypes.c_longlong if 'strtoll' in name else
                       ctypes.c_ulong if 'strtoul' in name else ctypes.c_long)
    buffer = ctypes.create_string_buffer(data)
    start = ctypes.addressof(buffer)
    end = ctypes.c_void_p(start)
    ctypes.set_errno(73)
    value = function(buffer, ctypes.byref(end), base)
    return value & ((1 << 64) - 1), end.value - start, ctypes.get_errno()

cases = []
edges = [b'', b' ', b'\t\n', b'+', b'-', b'+-', b'0', b'-0', b'0x', b'0xg',
         b'-0x1', b'0Xabcdef', b'0b101', b'0777', b'09', b'  +123z',
         b'\xff12', b'12\xff', b'9223372036854775807', b'9223372036854775808',
         b'-9223372036854775808', b'-9223372036854775809',
         b'18446744073709551615', b'18446744073709551616',
         b'-18446744073709551615', b'-18446744073709551616']
for data in edges:
    for base in [0, 2, 8, 10, 16, 36, 1, 37, -1]:
        cases.append((data, base))
digits = '0123456789abcdefghijklmnopqrstuvwxyz'
def encode(value, base):
    result = ''
    while value:
        result = digits[value % base] + result
        value //= base
    return result or '0'
for base in range(2, 37):
    for limit in [0, (1 << 63) - 1, 1 << 63, (1 << 64) - 1, 1 << 64]:
        for delta in [-1, 0, 1]:
            if limit + delta >= 0:
                for sign in ['', '-', '+']:
                    cases.append(((sign + encode(limit + delta, base)).encode(), base))
rng = random.Random(0x334216)
for i in range(2048):
    base = rng.randint(2, 36)
    text = encode(rng.getrandbits(rng.randint(1, 96)), base)
    if i & 1: text = text.upper()
    text = rng.choice(['', ' ', '\t\n']) + rng.choice(['', '+', '-']) + text
    if i % 3 == 0: text += '!tail'
    cases.append((text.encode(), base))

lines = ['struct integer_vector { const char *text; int base; '
         'unsigned long long signed_bits; unsigned signed_end; int signed_errno; '
         'unsigned long long unsigned_bits; unsigned unsigned_end; int unsigned_errno; };',
         'static const struct integer_vector integer_vectors[] = {']
for data, base in cases:
    answers = []
    for name in ['strtoll', 'strtoull']:
        expected = call(host, name, data, base)
        actual = call(port, 'nextstep_' + name, data, base)
        if actual != expected:
            raise SystemExit(repr((name, data, base, actual, expected)))
        answers.append(expected)
    literal = '"' + ''.join(chr(c) if 32 <= c < 127 and chr(c) not in '\\"'
                            else '\\%03o' % c for c in data) + '"'
    def fields(value):
        number, end, error = value
        return '0x%xULL,%d,%d' % (number, end, {73: 0, 34: 1, 22: 2}[error])
    lines.append('{%s,%d,%s,%s},' % (literal, base, fields(answers[0]), fields(answers[1])))
# Native long has the host's width here; target-width boundaries are also
# checked by libc-regressions.c in each real NeXT guest.
long_checks = 0
for data, base in cases:
    for name in ['strtol', 'strtoul']:
        expected = call(host, name, data, base)
        actual = call(port, 'ns33_' + name, data, base)
        if actual != expected:
            raise SystemExit(repr((name, data, base, actual, expected)))
        long_checks += 1
lines.append('};')
(out / 'integer-vectors.h').write_text('\n'.join(lines) + '\n')
ilp32_checks = 0
if a.check_ilp32:
    check = out / 'long32.c'
    check.write_text("""#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include "integer-vectors.h"
extern long ns33_strtol(const char *, char **, int);
extern unsigned long ns33_strtoul(const char *, char **, int);
int main(void) {
  unsigned i; char *a, *b; int ea, eb;
  if (sizeof(long) != 4) return 2;
  for (i=0; i<sizeof(integer_vectors)/sizeof(integer_vectors[0]); ++i) {
    const char *s=integer_vectors[i].text; int base=integer_vectors[i].base;
    long x,y; unsigned long u,v;
    a=b=(char *)s; errno=73; x=strtol(s,&a,base); ea=errno;
    errno=73; y=ns33_strtol(s,&b,base); eb=errno;
    if(x!=y || a!=b || ea!=eb) {printf("signed failure %u\\n",i);return 1;}
    a=b=(char *)s; errno=73; u=strtoul(s,&a,base); ea=errno;
    errno=73; v=ns33_strtoul(s,&b,base); eb=errno;
    if(u!=v || a!=b || ea!=eb) {printf("unsigned failure %u\\n",i);return 1;}
  }
  return 0;
}
""")
    subprocess.run(['cc', '-m32', '-O2', '-std=gnu17', '-c',
        '-Dstrtoll=port_strtoll', '-Dstrtoull=port_strtoull', '-Datoll=port_atoll',
        '-D_Exit=port__Exit', str(ROOT / 'src/integer-conversion.c'),
        '-o', str(out / 'long32.o')], check=True)
    subprocess.run(['cc', '-m32', '-O2', '-std=gnu17', str(check),
                    str(out / 'long32.o'), '-o', str(out / 'long32')], check=True)
    subprocess.run([str(out / 'long32')], check=True)
    ilp32_checks = 2 * len(cases)
(out / 'results.json').write_text(json.dumps({'vectors': len(cases),
    'differential_checks': 2 * len(cases) + long_checks + ilp32_checks,
    'ilp32_long_checks': ilp32_checks, 'failures': 0,
    'scope': 'C99 parsing, values, end pointers and errno against host libc'}, indent=2) + '\n')
print('Host differential checks passed:', 2 * len(cases) + long_checks + ilp32_checks)
