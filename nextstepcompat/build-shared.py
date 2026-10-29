#!/usr/bin/env python3
"""Build shared NextStepCompat with canonical public function entries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain',type=Path,required=True)
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();tc=a.toolchain.resolve();sdk=a.sdk.resolve();out=a.output.resolve()
if out.exists():p.error('Use a new output directory')
out.mkdir(parents=True)
record={'environment_source_sha256':hashlib.sha256((ROOT/'src/environment.c').read_bytes()).hexdigest(),'schema':2,'steps':[],'toolchain_manifest_sha256':hashlib.sha256((tc/'toolchain.json').read_bytes()).hexdigest(),'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
def run(*args):
 result=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 record['steps'].append({'command':list(map(str,args)),'exitcode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
 if result.returncode:raise RuntimeError(result.stderr)
objects=[]
component=out/'component'
run(sys.executable,ROOT/'build.py','--toolchain',tc,'--sdk',sdk,'--shared','--output',component)
record['component_record_sha256']=hashlib.sha256((component/'build-record.json').read_bytes()).hexdigest()
component_record=json.loads((component/'build-record.json').read_text())
if component_record.get('status')!='passed' or not component_record.get('canonical_shared'):
 raise ValueError('Require a successful canonical shared component')
for arch in ['m68k','i386','hppa','sparc']:
 path=component/arch/'libnextstepcompat.a'
 if hashlib.sha256(path.read_bytes()).hexdigest()!=component_record['targets'][arch]['archive_sha256']:
  raise ValueError('Shared component archive checksum mismatch: '+arch)
 directory=out/arch;directory.mkdir()
 archive=directory/'component.a';shutil.copy2(path,archive)
 obj=out/(arch+'.o')
 run(tc/'libexec/cctools/ld','-arch',arch,'-r','-all_load',archive,'-o',obj)
 objects.append(obj)
run(tc/'libexec/cctools/lipo','-create',*objects,'-output',out/'compat.o')
run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',ROOT/'shared.json',
    '--output',out/'libnextstepcompat.1.shlib','--import-library',out/'libnextstepcompat.a',
    '--build-record',out/'shared-build.json',out/'compat.o')
record['status']='passed'
record['artifacts_sha256']={name:hashlib.sha256((out/name).read_bytes()).hexdigest()
                          for name in ['libnextstepcompat.1.shlib','libnextstepcompat.a']}
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built NIHS shared NextStepCompat; runtime validation still required')
