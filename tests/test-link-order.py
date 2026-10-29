#!/usr/bin/env python3
"""Check ordered source, archive and -l operands with the installed driver."""
import argparse
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain',type=Path,required=True)
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();tc=a.toolchain.resolve();sdk=a.sdk.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
(out/'main.c').write_text('extern int first(void); int main(void) { return first()!=42; }\n')
(out/'first.c').write_text('extern int last(void); int first(void) { return last(); }\n')
(out/'last.c').write_text('int last(void) { return 42; }\n')
record=[]
for arch in ['i386','m68k','sparc','hppa']:
 d=out/arch;d.mkdir(exist_ok=True);cc=[str(tc/'bin/nextstep-gcc'),'--sdk',str(sdk),'-arch',arch,'-O2']
 for name in ['first','last']:
  subprocess.run(cc+['-c',str(out/(name+'.c')),'-o',str(d/(name+'.o'))],check=True)
  subprocess.run([str(tc/'libexec/cctools/libtool'),'-static','-o',str(d/('lib'+name+'.a')),str(d/(name+'.o'))],check=True)
 cases=[['-L'+str(d),'-lfirst',str(d/'liblast.a')],
        ['-L',str(d),'-l','first',str(d/'liblast.a')],
        ['-L'+str(d),'-Wl,-lfirst',str(d/'liblast.a')],
        ['-L'+str(d),'-Xlinker','-lfirst',str(d/'liblast.a')],
        [str(d/'libfirst.a'),'-L'+str(d),'-llast']]
 for index,flags in enumerate(cases):
  command=cc+[str(out/'main.c'),*flags,'-o',str(d/('test-'+str(index)))]
  r=subprocess.run(command,capture_output=True,text=True)
  record.append({'arch':arch,'case':index,'command':command,'exitcode':r.returncode,'stderr':r.stderr})
  if r.returncode:print(r.stderr);raise SystemExit('Link order failed '+arch+' '+str(index))
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(str(len(record))+' ordered link checks passed; this is a link test, not guest execution.')
