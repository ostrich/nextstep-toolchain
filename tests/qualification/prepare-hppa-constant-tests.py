#!/usr/bin/env python3
"""Build an optimized HPPA exact-constant and conditional-move regression."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--driver',type=Path,required=True)
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--compiler-build',type=Path)
p.add_argument('--host-tools',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
values=[0x4000+i*0x800 for i in range(8)]
values += [0x12344000+i*0x800 for i in range(8)]
values += [0x92344000+i*0x800 for i in range(8)]
values += [0xffffc000+i*0x800 for i in range(8)]
values += [0x12345678,0x89abcdef,0xffffffff,0x80000000]
code=['#include <stdio.h>','static volatile int select_value=1;']
for i,v in enumerate(values):
 code += [f'__attribute__((noinline,noclone)) unsigned f{i}(void) {{return 0x{v:08x}U;}}',
          f'__attribute__((noinline,noclone)) unsigned c{i}(int x) {{return x ? 0x{v:08x}U : 0;}}']
code += ['int main(void){unsigned got,want;int bad=0,total=0;']
for i,v in enumerate(values):
 code += [f'if(sscanf("{v:x}","%x",&want)!=1)return 2;',
          f'got=f{i}();total++;if(got!=want){{printf("FAIL direct {v:08x} got %08x\\n",got);bad++;}}',
          f'got=c{i}(select_value);total++;if(got!=want){{printf("FAIL conditional {v:08x} got %08x\\n",got);bad++;}}',
          f'got=c{i}(select_value-1);total++;if(got){{printf("FAIL zero {v:08x} got %08x\\n",got);bad++;}}']
code += ['printf("HPPA CONSTANTS: %d checks, %d failures\\n",total,bad);return bad!=0;}']
source=out/'constants.c';source.write_text('\n'.join(code)+'\n');commands=[]
base=[str(a.driver.resolve()),'--sdk',str(a.sdk.resolve()),'-arch','hppa']
for flag,path in [('--compiler-build',a.compiler_build),('--host-tools',a.host_tools)]:
 if path:base += [flag,str(path.resolve())]
for level in ['O1','O2','O3','Os']:
 cmd=base+['-'+level,str(source),'-o',str(out/level)]
 subprocess.run(cmd,check=True);commands.append({'command':cmd,'sha256':hashlib.sha256((out/level).read_bytes()).hexdigest()})
(out/'record.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':len(values)*3,'builds':commands},indent=2)+'\n')
print('Built four optimization levels, '+str(len(values)*3)+' checks each; guest execution remains required')
