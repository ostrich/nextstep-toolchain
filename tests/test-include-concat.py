#!/usr/bin/env python3
"""Exercise the NeXT quoted-header extension and surrounding diagnostics."""
import json
from pathlib import Path
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]
build = ROOT / 'work/build-i386/gcc'
out = ROOT / 'work/include-concat'
out.mkdir(parents=True, exist_ok=True)
(out / 'arch/i386').mkdir(parents=True, exist_ok=True)
header = '#define CONCAT_HEADER_OK 42\n'
(out / 'marker.h').write_text(header)
(out / 'arch/i386/marker.h').write_text(header)
(out / 'once.h').write_text('#ifdef IMPORT_SEEN\n#error duplicate import\n#endif\n#define IMPORT_SEEN 1\n' + header)
check = '\n#if CONCAT_HEADER_OK != 42\n#error wrong header selected\n#endif\nint probe;\n'
cases = [
    ('quoted', '#include "marker.h"', True, []),
    ('angle', '#include <marker.h>', True, []),
    ('adjacent', '#include "mark" "er.h"', True, []),
    ('architecture', '#define ARCH_INCLUDE(prefix, suffix) #prefix __ARCHITECTURE__ "/" #suffix\n#include ARCH_INCLUDE(arch/, marker.h)', True, []),
    ('macro-fragments', '#define PART "mark"\n#define REST "er.h"\n#include PART REST', True, []),
    ('comment', '#include "mark" /* comment */ "er.h"', True, []),
    ('kept-comment', '#include "mark" /* comment */ "er.h"', True, ['-C']),
    ('import-once', '#import "on" "ce.h"\n#import "on" "ce.h"', True, ['-Wno-deprecated']),
    ('trailing-name', '#include "marker.h" unexpected', False, []),
    ('angle-extra', '#include <marker.h> "unexpected"', False, []),
    ('empty', '#include ""', False, []),
]
records = {'patches_sha256': patch_hashes(ROOT), 'cases': []}
for language in ['c', 'c++', 'objective-c', 'objective-c++']:
    for name, text, expected, extra in cases:
        source = out / 'probe.c'
        source.write_text(text + check)
        command = [str(build / 'xgcc'), '-B' + str(build) + '/', '-x' + language,
                   '-E', '-P', '-Werror', '-I' + str(out)] + extra + [str(source)]
        r = subprocess.run(command, capture_output=True, text=True)
        passed = (r.returncode == 0) == expected
        records['cases'].append({'language': language, 'name': name,
                                 'passed': passed, 'exitcode': r.returncode,
                                 'stdout': r.stdout, 'stderr': r.stderr})
        print(language + ' ' + name + ': ' + ('PASS' if passed else 'FAIL'), flush=True)
records['compiler_sha256'] = {name: digest(build / name) for name in ['cc1', 'cc1plus', 'cc1obj', 'cc1objplus']}
(out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
if not all(item['passed'] for item in records['cases']):
    raise SystemExit(1)
