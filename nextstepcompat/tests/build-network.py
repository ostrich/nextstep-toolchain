#!/usr/bin/env python3
"""Build optimized IPv4 resolver regressions with real and fixture databases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','compat','output']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--shared',action='store_true')
a=p.parse_args();tc=a.toolchain.resolve();out=a.output.resolve();compat=a.compat.resolve()
if out.exists():p.error('Use a fresh output directory')
out.mkdir(parents=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record={'sources_sha256':{n:digest(ROOT/n) for n in ['tests/network.c','tests/mock-resolver.c','src/network.c']},'toolchain_manifest_sha256':digest(tc/'toolchain.json'),'steps':[],'shared':a.shared}
variants=['network'] if a.shared else ['network','network-mock']
for name in variants:
 probes=[]
 for arch in ['m68k','i386','hppa','sparc']:
  library=compat/'libnextstepcompat.a' if a.shared else compat/arch/'libnextstepcompat.a'
  target=out/(name+'-'+arch)
  cmd=[str(tc/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve()),'--compat-headers',str(ROOT/'include'),'-arch',arch,'-O2',str(ROOT/'tests/network.c')]
  if name=='network-mock':
   cmd+=['-DMOCK_RESOLVER','-Dh_errno=ns33_test_h_errno',*[ '-D'+n+'=ns33_test_'+n for n in ['gethostbyname','gethostbyaddr','getservbyname','getservbyport','ioctl']],str(ROOT/'src/network.c')]
  cmd += [str(library),'-o',str(target)]
  r=subprocess.run(cmd,capture_output=True,text=True)
  record['steps'].append({'command':cmd,'exitcode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'compat_sha256':digest(library)})
  (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
  if r.returncode:raise SystemExit(r.stderr)
  probes.append(target)
 subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*map(str,probes),'-output',str(out/name)],check=True)
record['probes_sha256']={name:digest(out/name) for name in variants};record['status']='built'
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
