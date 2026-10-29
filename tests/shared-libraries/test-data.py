#!/usr/bin/env python3
"""Build NIHS exported-data libraries and verify stable slots across growth."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import struct
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','output']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--mixed-slots',action='store_true')
a=p.parse_args();tc=a.toolchain.resolve();sdk=a.sdk.resolve();root=a.output.resolve();root.mkdir(parents=True,exist_ok=False)
arches=['m68k','i386','hppa','sparc'];steps=[]
def run(*args,expected=None,perturb=None):
 env=None if perturb is None else dict(os.environ,MALLOC_PERTURB_=str(perturb))
 result=subprocess.run(list(map(str,args)),capture_output=True,text=True,env=env)
 steps.append({'command':list(map(str,args)),'exitcode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 if perturb is not None:steps[-1]['malloc_perturb']=perturb
 (root/'commands.json').write_text(json.dumps(steps,indent=2)+'\n')
 if expected:
  assert result.returncode and expected in result.stderr,result.stderr
 elif result.returncode:raise RuntimeError(result.stderr)
 return result.stdout
spec={'install_name':'/usr/local/lib/libdatatest.1.shlib','minor_version':1,
      'canonical_entries':True,
      'addresses':{'text':'0x2a000000','data':'0x2a100000'},'segment_reservation':'0x100000',
      'exports':['_example','_example_getter',None],
      'data_exports':[{'name':'_exported_data','kind':'data','slot_size':256},
                      {'name':'_exported_table','kind':'const','slot_size':256},
                      {'name':'_exported_record','kind':'const','slot_size':256},
                      {'kind':'const','slot_size':256}]}
if a.mixed_slots: spec['data_exports'][2]['slot_size']=1024
for version in [1,2]:
 d=root/str(version);d.mkdir();current=dict(spec);current['minor_version']=version
 (d/'spec.json').write_text(json.dumps(current,indent=2)+'\n')
 private='int private_before[3]={1,2,3}; const int private_constant[3]={4,5,6};'
 if version==2:private='int private_before[300]={1,2,3}; const int private_constant[500]={4,5,6};'
 source=private+'''\nstruct record {const char *name; int (*operation)(int);};
int example(int);
int exported_data=3;
const int exported_table[2]={7,11};
const struct record exported_record={"data ABI",example};
int example(int n){return n+exported_data+ADDITION;}
int (*example_getter(void))(int){return example;}
'''.replace('ADDITION','0' if version==1 else '100')
 (d/'library.c').write_text(source)
 run(tc/'bin/nextstep-gcc','--sdk',sdk,'--shared-exports',d/'spec.json','-O2','-fno-common',
     *[v for arch in arches for v in ['-arch',arch]],'-c',d/'library.c','-o',d/'library.o')
 run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',d/'spec.json',
     '--output',d/'libdatatest.1.shlib','--import-library',d/'libdatatest.a',
     '--build-record',d/'build.json',d/'library.o',perturb=165)
records=[json.loads((root/str(version)/'build.json').read_text()) for version in [1,2]]
for arch in arches:
 for artifact in ['libdatatest.1.shlib','libdatatest.a']:
  external=run(tc/'libexec/cctools/nm','-arch',arch,'-g',root/'1'/artifact)
  assert '_ns33_shlib_body_' not in external,external
 thin_import=root/('import-'+arch+'.a')
 run(tc/'libexec/cctools/lipo',root/'1/libdatatest.a','-thin',arch,'-output',thin_import)
 archive=thin_import.read_bytes();cursor=8
 assert archive.startswith(b'!<arch>\n')
 while cursor<len(archive):
  header=archive[cursor:cursor+60]
  assert len(header)==60 and header[58:60]==b'`\n'
  assert all(header[start:start+size].strip()==b'0' for start,size in [(16,12),(28,6),(34,6)])
  assert header[40:48].strip()==b'100644'
  size=int(header[48:58]);cursor+=60+size+size%2
 first=records[0]['targets'][arch]['data_layout'];second=records[1]['targets'][arch]['data_layout']
 assert {n:v['address'] for n,v in first.items()}=={n:v['address'] for n,v in second.items()}
 assert first['_exported_data']['address']==0x2a100000
 assert first['_exported_table']['address']==0x2a080000
 assert first['_exported_record']['address']==(0x2a080400 if a.mixed_slots else 0x2a080100)
 # Inspect actual mapping protections, not merely the requested command flags.
 thin=root/('runtime-'+arch)
 run(tc/'libexec/cctools/lipo',root/'1/libdatatest.1.shlib','-thin',arch,'-output',thin)
 raw=thin.read_bytes();endian='<' if raw[:4]==b'\xce\xfa\xed\xfe' else '>';offset=28;found=False
 for _ in range(struct.unpack_from(endian+'I',raw,16)[0]):
  cmd,size=struct.unpack_from(endian+'II',raw,offset)
  if cmd==1 and raw[offset+8:offset+24].split(b'\0')[0]==b'__ABI':
   maximum,initial=struct.unpack_from(endian+'II',raw,offset+40)
   assert maximum==1 and initial==1;found=True
  if cmd==7:
   name_offset=struct.unpack_from(endian+'I',raw,offset+8)[0]
   end=raw.index(b'\0',offset+name_offset,offset+size)
   assert not any(raw[end+1:offset+size]),'Nonzero library-ID padding'
  offset+=size
 assert found
 print('PASS stable writable and read-only data slots '+arch)
(root/'consumer.c').write_text('''#include <stdio.h>
#include <string.h>
struct record {const char *name; int (*operation)(int);};
extern int exported_data;
extern const int exported_table[2];
extern const struct record exported_record;
extern int example(int);
extern int (*example_getter(void))(int);
int main(void){int value;
 if(exported_data!=3 || exported_table[0]!=7 || exported_table[1]!=11) return 1;
 if(strcmp(exported_record.name,"data ABI")) return 2;
 exported_data=9; value=exported_record.operation(2);
 if(value!=11 && value!=111) return 3;
 if(exported_record.operation!=example || example_getter()!=example) return 4;
 printf("data ABI callback %d, pointer equality %d\\n",value,exported_record.operation==example);
 return 0;}
''')
run(tc/'bin/nextstep-gcc','--sdk',sdk,'-O2',*[v for arch in arches for v in ['-arch',arch]],
    root/'consumer.c',root/'1/libdatatest.a','-o',root/'consumer')
replay=root/'replay';replay.mkdir()
run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',root/'1/spec.json',
    '--output',replay/'libdatatest.1.shlib','--import-library',replay/'libdatatest.a',
    '--build-record',replay/'build.json',root/'1/library.o',perturb=90)
hashes={}
for filename in ['libdatatest.1.shlib','libdatatest.a']:
 original=(root/'1'/filename).read_bytes()
 assert original==(replay/filename).read_bytes(),filename
 hashes[filename]=hashlib.sha256(original).hexdigest()
# A producer must opt into definition isolation; accepting ordinary objects
# would silently reintroduce the function-pointer identity failure.
invalid=root/'unisolated';invalid.mkdir()
run(tc/'bin/nextstep-gcc','--sdk',sdk,'-arch','i386','-O2','-c',
    root/'1/library.c','-o',invalid/'library.o')
run(tc/'bin/nextstep-shlib','--sdk',sdk,'--arch','i386','--spec',root/'1/spec.json',
    '--output',invalid/'runtime.shlib','--import-library',invalid/'import.a',
    '--build-record',invalid/'record.json',invalid/'library.o',expected='compile with --shared-exports')
assert not (invalid/'runtime.shlib').exists() and not (invalid/'import.a').exists()
collision=root/'collision.c'
collision.write_text('int example(int n){return n;} int ns33_shlib_body_example(int n){return n+1;}\n')
run(tc/'bin/nextstep-gcc','--sdk',sdk,'-arch','i386','--shared-exports',root/'1/spec.json',
    '-O2','-c',collision,'-o',root/'collision.o',expected='body name collision')
assert not (root/'collision.o').exists()

# Legacy codecs contain private static helpers sharing a public API name.
# Their references must remain local, with no public branch/body rewriting.
private_source=root/'private-name.c'
private_source.write_text('static __attribute__((noinline)) int example(int n){return n+40;}\nint private_caller(int n){return example(n); }\n')
for arch in arches:
 private_object=root/('private-'+arch+'.o')
 run(tc/'bin/nextstep-gcc','--sdk',sdk,'-arch',arch,'--shared-exports',root/'1/spec.json',
     '-O2','-fno-inline','-c',private_source,'-o',private_object)
 names=run(tc/'libexec/cctools/nm',private_object)
 assert re.search(r'(?m)^.*\bt _example$',names),names
 assert '_ns33_shlib_body_example' not in names,names
print('PASS private names matching public exports retain local linkage')

(root/'host-validation.json').write_text(json.dumps({'status':'passed','runtime_tested':False,
    'private_export_name_collision_tested':True,'reproducible_runtime_and_import':True,'replay_sha256':hashes},indent=2)+'\n')
