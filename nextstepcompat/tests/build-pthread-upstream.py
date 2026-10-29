#!/usr/bin/env python3
"""Build pinned Open POSIX tests with unchanged source and explicit timing scaffolding."""
import argparse, hashlib, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','compat','output']:
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();tc=a.toolchain.resolve();out=a.output.resolve()
out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent;upstream=here/'pthread-upstream'
pin=json.loads((upstream/'sources.json').read_text())
for name,sha in pin['files_sha256'].items():
    if hashlib.sha256((upstream/name).read_bytes()).hexdigest()!=sha:
        raise SystemExit('Changed upstream input: '+name)
record={'upstream_commit':pin['commit'],'steps':[],'scaffolding_sha256':{
    f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in
    [here/'pthread-upstream-main.c',here/'pthread-upstream-timing.h']}}
for source in sorted((upstream/'conformance/interfaces').glob('*/*.c')):
    name=source.parent.name+'-'+source.stem
    slices=[]
    for arch in ['m68k','i386','hppa','sparc']:
        target=out/(name+'-'+arch)
        cmd=[str(tc/'bin/nextstep-gcc'),'--sdk',str(a.sdk.resolve()),
             '--compat-headers',str(here.parent/'include'),'-arch',arch,'-O2','-std=gnu11',
             '-I'+str(upstream/'include'),'-include',str(here/'pthread-upstream-timing.h'),
             str(source),str(here/'pthread-upstream-main.c'),str(a.compat.resolve()/'libnextstepcompat.a'),
             '-o',str(target)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        record['steps'].append({'command':cmd,'exitcode':r.returncode,'stderr':r.stderr})
        (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
        if r.returncode:raise SystemExit(r.stderr)
        slices.append(str(target))
    subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*slices,'-output',str(out/name)],check=True)
record['status']='built'
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
