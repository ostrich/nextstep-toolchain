#!/usr/bin/env python3
"""Prepare upstream Monster-schema workloads and complete flatc output oracles."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--host-flatc', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
pin = json.loads((ROOT / 'tests/cxx-runtime/flatbuffers-source.json').read_text())
src = ROOT / ('work/app-sources/flatbuffers-' + pin['version'].removeprefix('v'))
out = a.output.resolve()
if out.exists():
    p.error('Use a new oracle directory')
out.mkdir(parents=True)
inputs = ['monster_test.fbs', 'monsterdata_test.json',
          'include_test/include_test1.fbs', 'include_test/sub/include_test2.fbs']
input_files = []
for name in inputs:
    relative = 'include/' + name[len('include_test/'):] if name.startswith('include_test/') else name
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / 'tests' / name, target)
    input_files.append(relative)
cases = [
    ('cpp', ['--cpp', '--gen-all', '--gen-object-api', '--gen-compare', '--reflect-names',
             '-I', 'include', '-o', 'cpp', 'monster_test.fbs'], ['cpp/monster_test_generated.h']),
    ('schema', ['--jsonschema', '-I', 'include', '-o', 'schema', 'monster_test.fbs'],
     ['schema/monster_test.schema.json']),
    ('binary', ['-b', '-I', 'include', '-o', 'binary', 'monster_test.fbs', 'monsterdata_test.json'],
     ['binary/monsterdata_test.mon']),
    ('json', ['-t', '--strict-json', '--defaults-json', '-I', 'include', '-o', 'json',
              'monster_test.fbs', '--', 'binary/monsterdata_test.mon'], ['json/monsterdata_test.json']),
    # The upstream annotation generator writes beside the input binary.
    ('annotate', ['--annotate', 'monster_test.fbs', '-I', 'include', '--',
                  'binary/monsterdata_test.mon'], ['binary/monsterdata_test.afb'])]
records = []
lines = ['struct flatc_file { const char *name; const unsigned char *data; unsigned size; };']
def array(name, data):
    lines.append('static const unsigned char ' + name + '[] = {')
    lines.extend(','.join(str(b) for b in data[i:i+24]) + ',' for i in range(0, len(data), 24))
    lines.append('};')
for i, name in enumerate(input_files):
    array('input' + str(i), (out / name).read_bytes())
lines.append('static const struct flatc_file inputs[] = {')
lines.extend('{"%s",input%d,sizeof(input%d)},' % (name, i, i) for i, name in enumerate(input_files))
lines.append('};')
for i, (name, args, outputs) in enumerate(cases):
    for filename in outputs:
        (out / filename).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(a.host_flatc.resolve()), *args], cwd=out, capture_output=True)
    (out / (name + '.log')).write_bytes(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit('Host flatc case failed: ' + name)
    lines.append('static const char *const args%d[] = {%s,0};' %
                 (i, ','.join(json.dumps(arg) for arg in ['flatc', *args])))
    for j, filename in enumerate(outputs):
        data = (out / filename).read_bytes()
        array('output%d_%d' % (i, j), data)
    lines.append('static const struct flatc_file outputs%d[] = {' % i)
    lines.extend('{"%s",output%d_%d,sizeof(output%d_%d)},' % (filename, i, j, i, j)
                 for j, filename in enumerate(outputs))
    lines.append('};')
    records.append({'name': name, 'arguments': args,
        'outputs': {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in outputs}})
lines.append('struct flatc_case { const char *name; const char *const *arguments; '
             'const struct flatc_file *outputs; unsigned count; };')
lines.append('static const struct flatc_case cases[] = {')
lines.extend('{"%s",args%d,outputs%d,sizeof(outputs%d)/sizeof(outputs%d[0])},' % (name, i, i, i, i)
             for i, (name, _, _) in enumerate(cases))
lines.append('};')
(out / 'flatc-cases.h').write_text('\n'.join(lines) + '\n')
# Compile and execute the host-generated C++ verifier against the host binary.
(out / 'generated.cc').write_text('''#include "monster_test_generated.h"
#include <cassert>
#include <fstream>
#include <iterator>
#include <vector>
int main() {
  std::ifstream input("binary/monsterdata_test.mon", std::ios::binary);
  std::vector<char> data((std::istreambuf_iterator<char>(input)), {});
  flatbuffers::Verifier v(reinterpret_cast<const uint8_t*>(data.data()), data.size());
  assert(MyGame::Example::VerifyMonsterBuffer(v));
  auto m = MyGame::Example::GetMonster(data.data());
  assert(m->hp() == 80 && m->name()->str() == "MyMonster");
}
''')
command = ['c++', '-O2', '-std=c++17', '-I' + str(src / 'include'), '-Icpp',
           'generated.cc', '-o', 'generated']
subprocess.run(command, cwd=out, check=True)
subprocess.run([str(out / 'generated')], cwd=out, check=True)
(out / 'cases.json').write_text(json.dumps({'upstream': pin, 'inputs': input_files,
    'cases': records, 'generated_verifier_assertions': 'passed on host'}, indent=2) + '\n')
print('Prepared five full-output workloads; generated C++ verifier assertions passed.')
