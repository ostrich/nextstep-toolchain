#!/usr/bin/env python3
"""Build a static fault fixture, replacing only the private waiter allocation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'compat', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
tc, out = a.toolchain.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
record = {'steps': [], 'inputs': {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
          for f in [root/'src/pthread-subset.c',root/'src/pthread-lifecycle.c',root/'src/pthread-internal.h',root/'tests/pthread-failures.c']}}
for arch in ['m68k', 'i386', 'hppa', 'sparc']:
    flags = [str(tc/'bin/nextstep-gcc'), '--sdk', str(a.sdk.resolve()),
             '--compat-headers', str(root/'include'), '-arch', arch, '-O2']
    obj = out/(arch+'.o')
    lifecycle = out/(arch+'-lifecycle.o')
    commands = [flags+['-Dcalloc=pt_test_calloc','-c',str(root/'src/pthread-lifecycle.c'),'-o',str(lifecycle)], flags+['-Dport_allocate=pt_test_port_allocate','-Dmalloc=pt_test_malloc','-Dfree=pt_test_free','-c',str(root/'src/pthread-subset.c'),'-o',str(obj)],
                flags+[str(root/'tests/pthread-failures.c'),str(obj),str(lifecycle),str(a.compat.resolve()/arch/'libnextstepcompat.a'),'-o',str(out/('failures-'+arch))]]
    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        record['steps'].append({'command': cmd, 'exitcode': result.returncode, 'stderr': result.stderr})
        (out/'build-record.json').write_text(json.dumps(record, indent=2)+'\n')
        if result.returncode:
            raise SystemExit(result.stderr)
subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*[str(out/('failures-'+a)) for a in ['m68k','i386','hppa','sparc']],'-output',str(out/'failures')],check=True)
record['sha256'] = hashlib.sha256((out/'failures').read_bytes()).hexdigest()
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
