#!/usr/bin/env python3
"""Accept complete, halted NIHS/OPENSTEP pthread batches and record public hashes."""
import argparse
import hashlib
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['suite','openstep','payload','runtime','component','toolchain','output']:
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
required=['PASS native pthread prerequisites:', 'PASS native spin_lock characterization:',
          'PASS threading subset:', 'PASS thread keys:',
          'PASS expanded pthread suite',
          'PASS terminated ownership is not inherited through native handle recycling',
          'PASS initial-thread pthread_exit, join value and zero final process status',
          'PASS C++ pthread/native linkage, ordinary RAII and lexical cleanup',
          'PASS fork failure callbacks and per-Cproc error preservation',
          'PASS pthread allocation failures:', 'PASS selected Open POSIX pthread tests']
upstream={'pthread_barrier_wait-1-1','pthread_cond_timedwait-1-1','pthread_join-1-1',
          'pthread_mutex_lock-1-1','pthread_mutex_trylock-1-1','pthread_once-1-1',
          'pthread_rwlock_rdlock-1-1','pthread_setspecific-1-1'}
payload=json.loads((a.payload/'payload.json').read_text())
record={'schema':1,'shared_minor':20,'runtime_sha256':digest(a.runtime),
        'static_build_record_sha256':digest(a.component/'build-record.json'),
        'toolchain_manifest_sha256':digest(a.toolchain/'toolchain.json'),
        'single_vcpu':True,'targets':{}}
for arch in ['m68k','i386','hppa','sparc','openstep-i386']:
    if arch=='openstep-i386':
        d=a.openstep;c=json.loads((d/'validation.json').read_text())
        clean=c.get('fsck_exitcode')==0
    else:
        d=a.suite/arch/'guest';c=json.loads((d/'collection.json').read_text())
        clean=bool(c.get('fsck')) and not any(c['fsck'].values())
        for name,sha in payload.items():
            if digest(a.suite/arch/'payload'/name)!=sha:
                p.error('Changed target payload: '+arch+'/'+name)
    if not c.get('passed') or not c.get('native_halt') or not clean:
        p.error('Incomplete or unclean collection: '+arch)
    lines=(d/'results.txt').read_text().splitlines()
    if 'PORTS-SUITE 0' not in lines or any(not any(line.startswith(marker) for line in lines) for marker in required):
        p.error('Missing complete test markers: '+arch)
    selected=[line[len('UPSTREAM '):] for line in lines if line.startswith('UPSTREAM ')]
    if len(selected)!=8 or set(selected)!=upstream:
        p.error('Incomplete selected upstream tests: '+arch)
    if arch=='sparc':
        cmd=json.loads((d/'command.json').read_text())
        clock=cmd[cmd.index('-icount')+1] if '-icount' in cmd else 'normal TCG'
    else:clock='normal TCG' if arch!='m68k' else 'Previous'
    record['targets'][arch]={'passed':True,'native_halt':True,'filesystem_clean':True,
                             'upstream_tests':8,'results_sha256':digest(d/'results.txt'),
                             'clock_mode':clock}
if payload.get('libnextstepcompat.1.shlib')!=record['runtime_sha256']:
    p.error('Test payload does not contain the selected runtime')
a.output.write_text(json.dumps(record,indent=2)+'\n')
print('PASS complete five-target pthread qualification, native halt and offline checks')
