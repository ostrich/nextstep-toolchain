#!/usr/bin/env python3
"""Prepare disposable NIHS guests for the shared dependency batch."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
TC=ROOT.parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ['build','lab','nextufs','intel-iso','intel-floppy','qemu-i386','previous-baseline','risc-iso']:
    p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--compat-build',type=Path,help='Shared compatibility runtime directory')
p.add_argument('--compat-tests',type=Path,help='Built shared compatibility regression directory')
p.add_argument('--display',type=int,default=224)
p.add_argument('--risc-preparer', type=Path, required=True,
               help='External RISC validation-CD preparation script')
a=p.parse_args()
if not a.risc_preparer.is_file():
    p.error('--risc-preparer must name an existing Python script')
lab,build,ufs=(x.resolve() for x in [a.lab,a.build,a.nextufs])
if lab.exists():p.error('Use a new lab directory')
if bool(a.compat_build)!=bool(a.compat_tests):p.error('Specify both compatibility inputs')
lab.mkdir(parents=True)
commands=[]
def run(cmd):
    cmd=list(map(str,cmd));commands.append(cmd);subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
def put(image,guest,source,mode='0755'):
    run([ufs,'mkfile','--from-file',image,guest,source])
    run([ufs,'mkfile','--chmod',image,guest,mode])
    if subprocess.check_output([str(ufs),'browse','--raw',str(image),guest])!=source.read_bytes():raise RuntimeError('Readback mismatch '+guest)
def library(image):
    for directory in ['/usr/local','/usr/local/lib']:
        if subprocess.run([str(ufs),'browse',str(image),directory],capture_output=True).returncode:
            run([ufs,'mkfile','--mkdir',image,directory])
    for name in ['leaf','left','right','top']:
        filename='libdep'+name+'.1.shlib'
        put(image,'/usr/local/lib/'+filename,build/filename)
    if a.compat_build:put(image,'/usr/local/lib/libnextstepcompat.1.shlib',a.compat_build.resolve()/'libnextstepcompat.1.shlib')
assets={name:build/name for name in ['consumer','require2','leaf-upgrade.shlib','run-dependencies.sh']}
if a.compat_tests:
    probes=json.loads((a.compat_tests/'build-record.json').read_text())['artifacts']
    assets.update({name:a.compat_tests.resolve()/name for name in probes})
    combined=lab/'run-combined.sh'
    script=assets['run-dependencies.sh'].read_text()
    script+='\nfor probe in '+' '.join(probes)+'; do\n'
    script+=' echo "RUN shared $probe"\n ./$probe "$1" || exit 80\ndone\necho "PASS combined shared batch complete"\n'
    combined.write_text(script);combined.chmod(0o755)
    assets['run-dependencies.sh']=combined
payload=lab/'payload';payload.mkdir()
for name,path in assets.items():shutil.copy2(path,payload/name)
run([sys.executable,TC/'tests/guest/prepare-intel33-vm.py','--iso',a.intel_iso,'--boot-floppy',a.intel_floppy,
     '--qemu',a.qemu_i386,'--lab',lab/'intel33','--nextufs',ufs,'--probes',payload,
     *[item for name in assets for item in ['--probe',name]]])
script=lab/'intel-run.sh';script.write_text('#!/bin/sh\n/etc/mount -n -o remount,rw /dev/hd0a / || exit 2\ncd /\n/bin/sh /run-dependencies.sh / > /dependency-results.txt 2>&1\n/bin/cat /dependency-results.txt\n/bin/sync\n/usr/etc/halt\n')
put(lab/'intel33/root.raw','/dependency-run.sh',script);library(lab/'intel33/root.raw')
run([sys.executable,TC/'tests/guest/prepare-previous33-vm.py','--baseline',a.previous_baseline,'--lab',lab/'previous33',
     '--nextufs',ufs,'--display',a.display,'--timeout','600','--discard-test-outputs',
     '--probe','run-dependencies.sh='+str(assets['run-dependencies.sh']),
     *[item for name,path in assets.items() if name!='run-dependencies.sh' for item in ['--asset',name+'='+str(path)]]])
library(lab/'previous33/disk.img')
cmd=[sys.executable,a.risc_preparer.resolve(),'--lab',lab/'risc33',
     '--iso',a.risc_iso,'--probes',TC/'work','--nextufs',ufs,'--only-extras','--writable-root']
for arch in ['sparc','hppa']:
    cmd+=['--extra',arch+':run-dependencies.sh='+str(assets['run-dependencies.sh']),'--argument',arch+':run-dependencies.sh=/gcc-tests/'+arch]
run(cmd)
image=lab/'risc33/media/ns33-validation.iso';library(image)
for arch in ['sparc','hppa']:
    for name,path in assets.items():
        if name!='run-dependencies.sh':put(image,'/gcc-tests/'+arch+'/'+name,path)
    d=lab/'risc33'/(arch+'-validation');d.mkdir();run([ufs,'mkimg',d/'report.raw','128M'])
(lab/'preparation.json').write_text(json.dumps({'commands':commands},indent=2)+'\n')
print('Prepared four isolated shared-library test guests')
