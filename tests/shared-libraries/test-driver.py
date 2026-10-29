#!/usr/bin/env python3
"""Exercise shared-library construction and invalid ABI specifications on Linux."""
import argparse
import json
from pathlib import Path
import stat
import subprocess
import tempfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain',type=Path,required=True)
p.add_argument('--sdk',type=Path,required=True)
a=p.parse_args();tc=a.toolchain.resolve();sdk=a.sdk.resolve()
with tempfile.TemporaryDirectory(prefix='shared-driver-test-') as temp:
 root=Path(temp);source=root/'example.c'
 source.write_text('int exported_data=1; int example(int n){return n+exported_data;}\n')
 obj=root/'example.o'
 cmd=[str(tc/'bin/nextstep-gcc'),'--sdk',str(sdk),'-O2',*[item for arch in ['m68k','i386','hppa','sparc'] for item in ['-arch',arch]],'-c',str(source),'-o',str(obj)]
 subprocess.run(cmd,check=True)
 baseline={'install_name':'/usr/local/lib/libsharedtest.1.shlib','minor_version':1,
           'addresses':{'text':'0x28200000','data':'0x28300000'},'segment_reservation':'0x00100000',
           'exports':['_example',None,None]}
 def run(name,changes=None,expected=None,objects=None,existing=False):
  d=root/name;d.mkdir();spec=dict(baseline);spec.update(changes or {});(d/'spec.json').write_text(json.dumps(spec))
  output=d/'runtime.shlib'
  if existing:output.write_bytes(b'KEEP')
  result=subprocess.run([str(tc/'bin/nextstep-shlib'),'--sdk',str(sdk),'--spec',str(d/'spec.json'),
   '--output',str(output),'--import-library',str(d/'import.a'),'--build-record',str(d/'build.json'),str(objects or obj)],capture_output=True,text=True)
  if expected:
   assert result.returncode and expected in result.stderr,(name,result.stderr)
   assert not (d/'import.a').exists()
   if existing:assert output.read_bytes()==b'KEEP'
   else:assert not output.exists()
  else:
   assert result.returncode==0,result.stderr
   assert stat.S_IMODE(output.stat().st_mode)==0o755
   subprocess.run([str(tc/'libexec/cctools/lipo'),str(output),'-verify_arch','m68k','i386','hppa','sparc'],check=True)
  print('PASS '+name)
 run('valid')
 run('duplicate',{'exports':['_example','_example']},'unique explicit')
 run('overlap',{'addresses':{'text':'0x28200000','data':'0x28200000'}},'nonoverlapping')
 run('public-data',{'exports':['_exported_data']},'non-function export')
 run('reservation-overflow',{'segment_reservation':'0x00002000'},'reservation')
 run('minor-version',{'minor_version':0},'Minor version')
 run('overwrite',expected='new output paths',existing=True)
 source.write_text('extern int not_in_this_sdk(void); int example(int n){return n+not_in_this_sdk();}\n')
 subprocess.run(cmd,check=True)
 run('unresolved',expected='Unresolved non-system dependency')
print('PASS all host shared-driver checks')
