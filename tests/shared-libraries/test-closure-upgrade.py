#!/usr/bin/env python3
"""Exercise a compatible runtime upgrade that adds a transitive dependency."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();tc,sdk,out=[x.resolve() for x in [a.toolchain,a.sdk,a.output]]
if out.exists():p.error('Use a fresh output directory')
out.mkdir(parents=True);steps=[]
def run(cmd,expected=None):
 cmd=list(map(str,cmd));r=subprocess.run(cmd,capture_output=True,text=True)
 steps.append({'command':cmd,'exitcode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 (out/'commands.json').write_text(json.dumps(steps,indent=2)+'\n')
 if expected:assert r.returncode and expected in r.stderr,r.stderr[-2000:]
 elif r.returncode:raise RuntimeError(r.stderr[-2000:])
 return r
arches=['m68k','i386','hppa','sparc'];archargs=[x for arch in arches for x in ['-arch',arch]]
for name,version,source in [('child',1,'int fixture_child(int n){return n*3;}'),
 ('parent-old',1,'int fixture_parent(int n){return n+1;}'),
 ('parent-new',2,'extern int fixture_child(int); int fixture_parent(int n){return fixture_child(n)+1;}')]:
 d=out/name;d.mkdir();parent=name.startswith('parent');stem='parent' if parent else 'child'
 spec={'install_name':'/usr/local/lib/libfixture'+stem+'.1.shlib','minor_version':version,
       'canonical_entries':True,'addresses':{'text':'0x2f000000' if parent else '0x2f200000',
       'data':'0x2f100000' if parent else '0x2f300000'},'segment_reservation':'0x100000',
       'exports':['_fixture_'+stem,None]}
 (d/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');(d/'library.c').write_text(source+'\n')
 run([tc/'bin/nextstep-gcc','--sdk',sdk,*archargs,'--shared-exports',d/'spec.json','-O2','-c',d/'library.c','-o',d/'library.o'])
 dependency=['--dependency',out/'child/libfixturechild.a'] if name=='parent-new' else []
 run([tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',d/'spec.json',*dependency,
      '--output',d/('libfixture'+stem+'.1.shlib'),'--import-library',d/('libfixture'+stem+'.a'),
      '--build-record',d/'build.json',d/'library.o'])
(out/'consumer.c').write_text('#include <stdio.h>\nextern int fixture_parent(int);\nint main(void){int n=fixture_parent(2); printf("closure value %d\\n",n); return n!=7;}\n')
libs=[out/'parent-old/libfixtureparent.a',out/'parent-new/libfixtureparent.a']
loads={}
def validate_loads(name):
 for arch in arches:
  thin=out/(arch+'-'+name);run([tc/'libexec/cctools/lipo',out/name,'-thin',arch,'-output',thin])
  raw=thin.read_bytes();e='<' if raw[:4]==b'\xce\xfa\xed\xfe' else '>';cursor=28;identities={}
  for _ in range(struct.unpack_from(e+'I',raw,16)[0]):
   c,z=struct.unpack_from(e+'II',raw,cursor)
   if c==6:
    n,v,address=struct.unpack_from(e+'III',raw,cursor+8);identity=raw[cursor+n:cursor+z].split(b'\0')[0].decode()
    assert identity not in identities;identities[identity]=v
   cursor+=z
  assert identities['/usr/local/lib/libfixtureparent.1.shlib']==2
  assert identities['/usr/local/lib/libfixturechild.1.shlib']==1
  loads[arch+'-'+name]=identities

for name,order in [('old-first',libs),('new-first',list(reversed(libs)))]:
 run([tc/'bin/nextstep-gcc','--sdk',sdk,*archargs,'-O2',out/'consumer.c',*order,'-o',out/name])
 validate_loads(name)
# Force every metadata member, including duplicate __.FVMLIB_REF entries.
for arch in arches:
 for name,order in [('old-first',libs),('new-first',list(reversed(libs)))]:
  run([tc/'bin/nextstep-gcc','--sdk',sdk,'-arch',arch,'-nostdlib','-r','-Wl,-all_load',
       *order,'-o',out/(arch+'-all-load-'+name+'.o')])
for name in ['old-first','new-first']:
 run([tc/'libexec/cctools/lipo','-create',
      *[out/(arch+'-all-load-'+name+'.o') for arch in arches],'-output',out/('all-imports-'+name+'.o')])
 run([tc/'bin/nextstep-gcc','--sdk',sdk,*archargs,'-O2',out/'consumer.c',
      out/('all-imports-'+name+'.o'),'-o',out/('all-load-'+name)])
 validate_loads('all-load-'+name)
(out/'load-validation.json').write_text(json.dumps(loads,indent=2)+'\n')
# Ordinary equal-valued absolutes and real code definitions must still fail.
(out/'ordinary.s').write_text('.globl _ordinary_duplicate\n_ordinary_duplicate=17\n')
run([tc/'bin/nextstep-gcc','--sdk',sdk,*archargs,'-c',out/'ordinary.s','-o',out/'ordinary-a.o'])
(out/'ordinary-b.o').write_bytes((out/'ordinary-a.o').read_bytes())
run([tc/'bin/nextstep-gcc','--sdk',sdk,'-arch','i386','-nostdlib','-r',out/'ordinary-a.o',out/'ordinary-b.o','-o',out/'invalid-absolute.o'],expected='multiple definitions')
(out/'ordinary.c').write_text('int ordinary_text(void){return 1;}\n__asm__(".globl .file_definition_fixture\\n.file_definition_fixture=0");\n')
run([tc/'bin/nextstep-gcc','--sdk',sdk,*archargs,'-O2','-c',out/'ordinary.c','-o',out/'text-a.o'])
(out/'text-b.o').write_bytes((out/'text-a.o').read_bytes())
run([tc/'bin/nextstep-gcc','--sdk',sdk,'-arch','i386','-nostdlib','-r',out/'text-a.o',out/'text-b.o','-o',out/'invalid-code.o'],expected='multiple definitions')
(out/'results.json').write_text(json.dumps({'status':'passed','targets':arches,'link_orders':2,
 'highest_parent_minor':2,'transitive_child_loaded':True,'ordinary_conflicts_rejected':True,
 'toolchain_manifest_sha256':hashlib.sha256((tc/'toolchain.json').read_bytes()).hexdigest()},indent=2)+'\n')
print('PASS NIHS closure upgrade, dependency union, version floor and ordinary conflict checks')
