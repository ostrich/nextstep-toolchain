#!/usr/bin/env python3
"""Build existing compatibility regressions against the shared import archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','shared','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();tc=a.toolchain.resolve();sdk=a.sdk.resolve();shared=a.shared.resolve();out=a.output.resolve()
out.mkdir(parents=True,exist_ok=False)
record={'steps':[],'artifacts':{}}
probes={'compat-smoke':ROOT/'tests/shared-libraries/compat-smoke.c'}
for name in ['smoke','libc-regressions','regex','singlebyte','signals','fifo','groups','termios']:
 probes['api-'+name]=ROOT/'nextstepcompat/tests'/(name+'.c')
for name,source in probes.items():
 cmd=[tc/'bin/nextstep-gcc','--sdk',sdk,'-O2','-DNS33_EXTENDED',
      *[v for arch in ['m68k','i386','hppa','sparc'] for v in ['-arch',arch]],
      source,shared/'libnextstepcompat.a','-o',out/name]
 result=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
 record['steps'].append({'command':list(map(str,cmd)),'exitcode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
 if result.returncode:raise RuntimeError(result.stderr)
 record['artifacts'][name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
record['runtime_sha256']=hashlib.sha256((shared/'libnextstepcompat.1.shlib').read_bytes()).hexdigest()
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built '+str(len(probes))+' shared compatibility regressions for NIHS')
