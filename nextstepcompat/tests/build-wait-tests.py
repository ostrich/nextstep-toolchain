#!/usr/bin/env python3
"""Build optimized NIHS native wait4 observations and waitpid regression tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','sdk','output']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--shared',type=Path,help='Test a constructed NextStepCompat shared runtime')
p.add_argument('--probes-only',action='store_true',help='Observe native kernels without running the candidate implementation')
a=p.parse_args();tc,sdk,out=[x.resolve() for x in [a.toolchain,a.sdk,a.output]]
out.mkdir(parents=True,exist_ok=False)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
record={'toolchain_manifest_sha256':digest(tc/'toolchain.json'),'sources_sha256':{str(n.relative_to(ROOT)):digest(n) for n in [ROOT/'tests/waitpid-candidate.c',ROOT/'tests/waitpid.c',ROOT/'tests/probe-wait4.c',ROOT/'tests/probe-wait-interrupt.c']},'steps':[]}
programs=[('native-wait4',ROOT/'tests/probe-wait4.c'),('native-wait-interrupt',ROOT/'tests/probe-wait-interrupt.c')]
if not a.probes_only:programs.append(('waitpid-test',ROOT/'tests/waitpid.c'))
for name,source in programs:
    slices=[]
    for arch in ['m68k','i386','hppa','sparc']:
        target=out/(name+'-'+arch)
        command=[str(tc/'bin/nextstep-gcc'),'--sdk',str(sdk),'-arch',arch,'-O2',str(source)]
        if name=='waitpid-test':
            command += [str(a.shared.resolve()/'libnextstepcompat.a')] if a.shared else [str(ROOT/'tests/waitpid-candidate.c')]
        command+=['-o',str(target)]
        r=subprocess.run(command,capture_output=True,text=True)
        record['steps'].append({'command':command,'exitcode':r.returncode,'output':r.stdout+r.stderr})
        (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
        if r.returncode:raise SystemExit(r.stdout+r.stderr)
        slices.append(str(target))
    subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',*slices,'-output',str(out/name)],check=True)
script=out/'run-codecs.sh'
script.write_text('cd "$1" || exit 90\n'+''.join('./'+name+' || exit 1\n' for name,_ in programs)+'echo "PASS wait syscall regression batch complete"\n')
assets={n:str(out/n) for n in [*[name for name,_ in programs],'run-codecs.sh']}
record['scope']='Native kernel observations, not POSIX conformance' if a.probes_only else 'Candidate waitpid regression'
(out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
libraries={'libnextstepcompat.1.shlib':str(a.shared.resolve()/'libnextstepcompat.1.shlib')} if a.shared else {}
suite={'libraries':libraries,'assets':assets,'entry':'run-codecs.sh','success_marker':'PASS wait syscall regression batch complete','sha256':{n:digest(Path(f)) for n,f in {**libraries,**assets}.items()}}
(out/'suite.json').write_text(json.dumps(suite,indent=2)+'\n')
print('Built NIHS wait syscall tests; runtime verification pending')
