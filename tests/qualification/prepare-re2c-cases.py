#!/usr/bin/env python3
"""Generate reference files and run their upstream assertions on the host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--host-re2c', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
pin = json.loads((ROOT / 'tests/cxx-runtime/re2c-source.json').read_text())
version = subprocess.check_output([str(a.host_re2c.resolve()), '--version'], text=True).strip()
if version != 're2c ' + pin['version']:
    raise SystemExit('Host reference version does not match the pinned release')
src = ROOT / ('work/app-sources/re2c-' + pin['version'] + '/examples/c')
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
tests = [('01_basic.re', False), ('conditions/parse_u32_conditions.re', True),
         ('submatch/01_stags.re', False), ('submatch/02_mtags.re', False),
         ('submatch/04_posix_captures.re', False),
         ('submatch/http_rfc7230.re', False), ('submatch/uri_rfc3986.re', False)]
lines = ['struct re2c_case { const char *name; const unsigned char *input; '
         'unsigned input_size; const unsigned char *expected; '
         'unsigned expected_size; int conditions; };']
records = []
for i, (name, conditions) in enumerate(tests):
    data = (src / name).read_bytes()
    (out / 'input.re').write_bytes(data)
    command = [str(a.host_re2c.resolve()), '--no-generation-date', '--no-version', '-i']
    if conditions:
        command += ['-c']
    command += ['input.re', '-o', 'output.c']
    subprocess.run(command, cwd=out, check=True)
    expected = (out / 'output.c').read_bytes()
    subprocess.run(['c++', '-O2', 'output.c', '-o', 'scanner'], cwd=out, check=True)
    subprocess.run([str(out / 'scanner')], cwd=out, check=True)
    for label, content in [('input', data), ('expected', expected)]:
        lines.append('static const unsigned char ' + label + str(i) + '[] = {')
        lines += [','.join(str(v) for v in content[j:j+24]) + ','
                  for j in range(0, len(content), 24)]
        lines.append('};')
    records.append({'upstream_example': name, 'conditions': conditions,
                    'input_sha256': hashlib.sha256(data).hexdigest(),
                    'output_sha256': hashlib.sha256(expected).hexdigest(),
                    'generated_scanner_assertions': 'passed on host'})
lines.append('static const struct re2c_case cases[] = {')
for i, (name, conditions) in enumerate(tests):
    lines.append('{"' + name + '",input' + str(i) + ',sizeof(input' + str(i) + '),'
                 'expected' + str(i) + ',sizeof(expected' + str(i) + '),'
                 + str(int(conditions)) + '},')
lines.append('};')
(out / 're2c-cases.h').write_text('\n'.join(lines) + '\n')
(out / 'cases.json').write_text(json.dumps({'upstream': pin, 'cases': records,
    'host_re2c_sha256': hashlib.sha256(a.host_re2c.read_bytes()).hexdigest()}, indent=2) + '\n')
print('Prepared ' + str(len(tests)) + ' complete-output cases; generated scanner assertions passed.')
