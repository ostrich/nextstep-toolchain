#!/usr/bin/env python3
"""Build optimized threading/byte-order probes against a component or shared SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','compat','output']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--shared',action='store_true')
p.add_argument('--source', choices=['threads', 'thread-keys', 'pthread-expanded', 'pthread-native', 'pthread-native-spin', 'pthread-exit', 'pthread-cxx'], default='threads')
a=p.parse_args();tc=a.toolchain.resolve();out=a.output.resolve();compat=a.compat.resolve()
if out.exists():p.error('Use a fresh output directory')
out.mkdir(parents=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/('tests/'+a.source+('.cc' if a.source=='pthread-cxx' else '.c'))
compiler='nextstep-g++' if a.source=='pthread-cxx' else 'nextstep-gcc'
record={'source_sha256':digest(source),'toolchain_manifest_sha256':digest(tc/'toolchain.json'),'steps':[],'shared':a.shared}
probes=[]
for arch in ['m68k','i386','hppa','sparc']:
 library=compat/'libnextstepcompat.a' if a.shared else compat/arch/'libnextstepcompat.a'
 target=out/('threads-'+arch)
 cmd=[str(tc/'bin'/compiler),'--sdk',str(a.sdk.resolve()),'--compat-headers',str(ROOT/'include'),'-arch',arch,'-O2',str(source),str(library),'-o',str(target)]
 r=subprocess.run(cmd,capture_output=True,text=True)
 record['steps'].append({'command':cmd,'exitcode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'compat_sha256':digest(library)})
 (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
 if r.returncode:raise SystemExit(r.stderr)
 probes.append(target)
subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*map(str,probes),'-output',str(out/'threads')],check=True)
record['probe_sha256']=digest(out/'threads');record['status']='built'
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
