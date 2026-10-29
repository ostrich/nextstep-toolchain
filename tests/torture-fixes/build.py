#!/usr/bin/env python3
"""Build a compact native regression payload for compiler torture fixes."""
import argparse
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
for n in ['toolchain','sdk','source','output']:p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--arch',action='append',choices=['i386','m68k','hppa','sparc'])
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
tests={f.stem:f for f in Path(__file__).resolve().parent.glob('*.c')}
s=a.source/'gcc/testsuite/gcc.c-torture/execute'
for n in ['pr64242','complex-5','nestfunc-3','nestfunc-5','nestfunc-6','20000822-1']:tests[n]=s/(n+'.c')
lines=['#!/bin/sh','case "$0" in */*) place=`echo "$0" | /bin/sed \'s|/[^/]*$||\'`;cd "$place" || exit 90;;esac']
for name,source in tests.items():
 for opt in ['0','2']:
  n=name+'-O'+opt
  cmd=[str(a.toolchain.resolve()/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve())]
  for arch in a.arch or ['i386','m68k','hppa','sparc']:cmd+=['-arch',arch]
  cmd+=['-O'+opt,str(source.resolve()),'-o',str(out/n)]
  z=subprocess.run(cmd,capture_output=True,text=True);(out/(n+'.build.log')).write_text(z.stderr)
  if z.returncode:raise SystemExit(z.stderr)
  lines+=['echo BEGIN-'+n,'./'+n+' || exit 91','echo PASS-'+n]
(out/'run.sh').write_text('\n'.join(lines+['echo PORTS-SUITE 0'])+'\n');(out/'run.sh').chmod(0o755)
