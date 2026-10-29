#!/usr/bin/env python3
"""Check public branch addresses, loader records and unchanged consumers."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain',type=Path,required=True)
p.add_argument('--build',type=Path,required=True)
p.add_argument('--tests',type=Path,required=True)
p.add_argument('--spec',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();spec=json.loads(a.spec.read_text());exports=[n for n in spec['exports'] if n]
nm=a.toolchain.resolve()/'libexec/cctools/nm';lipo=nm.parent/'lipo'
results={}
for arch in ['m68k','i386','hppa','sparc']:
 def symbols(path):
  text=subprocess.check_output([str(nm),'-arch',arch,'-g',str(path)],text=True)
  return {t[2]:(t[1],int(t[0],16)) for line in text.splitlines() if len(t:=line.split())==3}
 old=symbols(a.build/'libbz2.a');new=symbols(a.tests/arch/'upgrade.a');exe=symbols(a.build/'bzip2')
 assert all(old[n][0]=='A' and old[n]==new[n] for n in exports),arch
 assert all(exe[n]==old[n] for n in exe if n in exports),arch
 thin=a.output.parent/('consumer-'+arch)
 subprocess.run([str(lipo),str(a.build/'bzip2'),'-thin',arch,'-output',str(thin)],check=True)
 raw=thin.read_bytes();thin.unlink();endian='<' if raw[:4]==b'\xce\xfa\xed\xfe' else '>'
 header=struct.unpack_from(endian+'7I',raw);offset=28;loads=[]
 for _ in range(header[4]):
  command,size=struct.unpack_from(endian+'2I',raw,offset)
  if command==6:
   name,minor,addr=struct.unpack_from(endian+'3I',raw,offset+8)
   path=raw[offset+name:offset+size].split(b'\0')[0].decode();loads.append({'path':path,'minor':minor,'address':addr})
  offset+=size
 assert any(x['path']==spec['install_name'] and x['minor']==spec['minor_version'] for x in loads),arch
 results[arch]={'exports':len(exports),'stable_branch_addresses':True,'consumer_load_commands':loads}
a.output.write_text(json.dumps(results,indent=2)+'\n');print('PASS stable public ABI and shared loader records on all four targets')
