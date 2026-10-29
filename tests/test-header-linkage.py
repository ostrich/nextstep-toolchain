#!/usr/bin/env python3
"""Check implicit C linkage for legacy system headers and normal C++ includes."""
import json
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]
build = ROOT / 'work/build-i386/gcc'
out = ROOT / 'work/header-linkage'
(out / 'system').mkdir(parents=True, exist_ok=True)
(out / 'ordinary').mkdir(exist_ok=True)
(out / 'system/api.h').write_text('extern int legacy_api(int);\n')
(out / 'ordinary/overloads.h').write_text('extern int ordinary(int);\nextern int ordinary(double);\n')
source = out / 'probe.cc'
source.write_text('#include <api.h>\n#include <overloads.h>\nint probe(int x) { return legacy_api(x) + ordinary(x) + ordinary(1.5); }\n')
record = {'patches_sha256': patch_hashes(ROOT), 'cases': []}
for language, frontend in [('c++', 'cc1plus'), ('objective-c++', 'cc1objplus')]:
    assembly = out / (frontend + '.s')
    command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-O2', '-fno-exceptions',
               '-fno-rtti', '-nostdinc', '-x' + language,
               '-isystem', str(out / 'system'), '-I', str(out / 'ordinary'),
               '-S', str(source), '-o', str(assembly)]
    r = subprocess.run(command, capture_output=True, text=True)
    text = assembly.read_text() if r.returncode == 0 else ''
    passed = (r.returncode == 0 and '_legacy_api' in text
              and '__Z10legacy_api' not in text
              and '__Z8ordinaryi' in text and '__Z8ordinaryd' in text)
    record['cases'].append({'language': language, 'command': command, 'passed': passed,
                            'exitcode': r.returncode, 'stderr': r.stderr,
                            'compiler_sha256': digest(build / frontend)})
    print(language + ': ' + ('PASS' if passed else 'FAIL'))
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
if not all(case['passed'] for case in record['cases']):
    raise SystemExit(1)
