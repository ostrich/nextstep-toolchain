#!/usr/bin/env python3
"""Build the focused NIHS hidden-argument/prologue batch and Intel control."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain',type=Path,default=ROOT/'install/current')
p.add_argument('--baseline',type=Path,required=True,help='Pre-fix compiler bundle for the Intel negative control')
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
tc,baseline,sdk,out=[x.resolve() for x in (a.toolchain,a.baseline,a.sdk,a.output)]
out.mkdir(parents=True,exist_ok=False)
payload=out/'payload';payload.mkdir()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
source=Path(__file__).with_name('prologues.c')
record={'toolchain_manifest_sha256':sha(tc/'toolchain.json'),'baseline_manifest_sha256':sha(baseline/'toolchain.json'),'source_sha256':sha(source),'commands':[]}
def build(pair):
    arch,opt=pair;directory=out/arch;directory.mkdir(exist_ok=True)
    base=[str(tc/'bin/nextstep-gcc'),'--sdk',str(sdk),'-arch',arch,'-'+opt,'-fstack-clash-protection','-DTEST_ARCH="'+arch+'"',str(source)]
    commands=[]
    for suffix,flags in [('',[]),('.s',['-S'])]:
        dest=directory/('prologues-'+opt+suffix);cmd=base+flags+['-o',str(dest)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        (directory/('prologues-'+opt+suffix+'.log')).write_text(r.stdout+r.stderr)
        commands.append({'argv':cmd,'exitcode':r.returncode,'diagnostics':r.stderr})
        if r.returncode:raise RuntimeError('Build failed: '+str(dest))
    return commands
with ThreadPoolExecutor(4) as pool:
    for commands in pool.map(build,[(arch,opt) for arch in ['i386','m68k','hppa','sparc'] for opt in ['O1','O2','O3']]):record['commands']+=commands
for opt in ['O1','O2','O3']:
    subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*[str(out/arch/('prologues-'+opt)) for arch in ['i386','m68k','hppa','sparc']],'-output',str(payload/('prologues-'+opt))],check=True)
cmd=[str(baseline/'bin/nextstep-gcc'),'--sdk',str(sdk),'-arch','i386','-O1','-fstack-clash-protection',str(ROOT/'tests/i386-stack-probe-sret.c'),'-o',str(payload/'intel-negative')]
subprocess.run(cmd,check=True);record['commands'].append({'argv':cmd,'exitcode':0})
(payload/'run.sh').write_text('''#!/bin/sh
case "$0" in */*) payload=`echo "$0" | /bin/sed 's|/[^/]*$||'` ;; *) payload=. ;; esac
cd "$payload" || exit 90
arch=`./prologues-O1 --arch` || exit 91
for opt in O1 O2 O3; do
 echo "RUN $arch $opt"
 ./prologues-$opt || exit 1
done
if test "$arch" = i386; then
 ./intel-negative
 status=$?
 if test "$status" != 1; then echo "FAIL negative control status $status"; exit 2; fi
 echo "PASS Intel old-compiler negative control"
fi
echo PORTS-SUITE 0
''')
record['payload_sha256']={f.name:sha(f) for f in payload.iterdir()}
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
print(payload,flush=True)
