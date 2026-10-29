#!/usr/bin/env python3
"""Check public driver header wrapping, including application include_next."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
tc, sdk, out = [path.resolve() for path in [a.toolchain, a.sdk, a.output]]
out.mkdir(parents=True, exist_ok=False)
fixture = out / 'application'
fixture.mkdir()
(fixture / 'limits.h').write_text('#define APPLICATION_WRAPPER 1\n#include_next <limits.h>\n')
source = out / 'probe.c'
source.write_text('''#include <limits.h>
#include <stdint.h>
#include <pthread.h>
#include <sched.h>
#include <pthread.h>
#ifdef __cplusplus
#include <climits>
#include <limits>
#endif
#ifndef PATH_MAX
#error SDK POSIX limits were hidden
#endif
#if CHAR_BIT != 8 || INT_MAX != 2147483647 || PATH_MAX != 1024
#error Incorrect target limits
#endif
#if EXPECT_APPLICATION && !defined(APPLICATION_WRAPPER)
#error Application wrapper was bypassed
#endif
typedef char target_size[(sizeof(intptr_t) == 4) ? 1 : -1];
int probe(void) { return PATH_MAX; }
''')
record = {'toolchain_manifest_sha256': hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest(),
          'steps': [], 'runtime_executed': False}
for arch in ['m68k', 'i386', 'hppa', 'sparc']:
    for language in ['c', 'c++']:
        for app in [False, True]:
            name = arch + '-' + language.replace('+', 'x') + ('-app' if app else '')
            cmd = [tc / 'bin/nextstep-gcc', '--sdk', sdk, '-arch', arch, '-O2', '-x', language]
            if app:
                cmd += ['-I', fixture, '-DEXPECT_APPLICATION=1']
            cmd += ['-S', source, '-o', out / (name + '.s')]
            result = subprocess.run(list(map(str, cmd)), capture_output=True, text=True)
            record['steps'].append({'command': list(map(str, cmd)), 'exitcode': result.returncode,
                                    'stdout': result.stdout, 'stderr': result.stderr})
            (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
            if result.returncode:
                raise SystemExit(result.stderr)
            print('PASS ' + name)
record['status'] = 'passed'
(out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
