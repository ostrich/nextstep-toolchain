#!/usr/bin/env python3
"""Reject incompatible shared identities and conflicting fixed-VM symbol values."""
import argparse
import runpy
import json
from pathlib import Path
import struct
import subprocess
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','fixture','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();tc,sdk,fixture,out=[n.resolve() for n in [a.toolchain,a.sdk,a.fixture,a.output]]
if out.exists():p.error('Use a fresh output directory')
out.mkdir(parents=True);results=[]
m=runpy.run_path(str(tc/'bin/nextstep-shlib'),run_name='import_metadata')
def run(cmd,expected=None):
 cmd=list(map(str,cmd));v=subprocess.run(cmd,capture_output=True,text=True)
 results.append({'command':cmd,'exitcode':v.returncode,'stdout':v.stdout,'stderr':v.stderr})
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 if expected:assert v.returncode and expected in v.stderr,v.stderr[-2000:]
 else:assert v.returncode==0,v.stderr
for name,source in [('parent',fixture/'parent-old/libfixtureparent.a'),('parent-new',fixture/'parent-new/libfixtureparent.a'),('child',fixture/'child/libfixturechild.a')]:
 run([tc/'libexec/cctools/lipo',source,'-thin','i386','-output',out/(name+'.a')])
def mutate(source,destination,kind):
 raw=(out/source).read_bytes();output=bytearray(b'!<arch>\n');changed=0
 for header,prefix,body in m['_archive_members'](raw):
  if body[:4] in (b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xce'):
   e='<' if body[:4]==b'\xce\xfa\xed\xfe' else '>';data=bytearray(body);cursor=28
   for _ in range(struct.unpack_from(e+'I',data,16)[0]):
    command,size=struct.unpack_from(e+'II',data,cursor)
    if command==6 and kind in ['header','overlap']:
     value=struct.unpack_from(e+'I',data,cursor+16)[0]
     struct.pack_into(e+'I',data,cursor+16,0x2f000000 if kind=='overlap' else value+0x2000);changed+=1
    if command==1 and kind in ['mapping','overlap']:
     address=struct.unpack_from(e+'I',data,cursor+24)[0]
     if address in (0x2f000000,0x2f200000):
      struct.pack_into(e+'I',data,cursor+24,0x2f000000 if kind=='overlap' else address+0x2000);changed+=1
    if command==2 and kind=='symbol':
     so,n,st,sz=struct.unpack_from(e+'4I',data,cursor+8);strings=bytes(data[st:st+sz])
     for index in range(n):
      pos=so+12*index;s,k,se,d,value=struct.unpack_from(e+'IBBhI',data,pos)
      if k==3 and strings[s:].split(b'\0')[0]==b'_fixture_parent':
       struct.pack_into(e+'I',data,pos+8,value+4);changed+=1
    cursor+=size
   body=bytes(data)
  output+=header+prefix+body
  if (len(prefix)+len(body))%2:output+=b'\n'
 assert changed>0
 (out/destination).write_bytes(output)
for kind in ['header','mapping','symbol']:mutate('parent.a','bad-'+kind+'.a',kind)
mutate('child.a','bad-overlap.a','overlap')
cc=[tc/'bin/nextstep-gcc','--sdk',sdk,'-arch','i386','-nostdlib','-r']
for kind in ['header','mapping']:
 run([*cc,out/'parent.a',out/('bad-'+kind+'.a'),'-o',out/('invalid-'+kind+'.o')],expected='Conflicting dependency identity')
run([*cc,out/'parent.a',out/'bad-overlap.a','-o',out/'invalid-overlap.o'],expected='Overlapping dependency mappings')
run([*cc,'-Wl,-all_load',out/'bad-symbol.a',out/'parent-new.a','-o',out/'invalid-symbol.o'],expected='multiple definitions of symbol _fixture_parent')
# Direct linker callers also retain identity checks when all members are loaded.
for kind in ['header','mapping']:
 run([tc/'libexec/cctools/ld','-arch','i386','-r','-all_load',out/'parent.a',out/('bad-'+kind+'.a'),'-o',out/('invalid-direct-'+kind+'.o')],expected='conflicting identity for fixed VM library')
print('PASS incompatible headers, mappings, overlap and symbol definitions rejected')
