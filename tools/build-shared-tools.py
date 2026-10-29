#!/usr/bin/env python3
"""Build the pinned fixed-VM library constructor using canonical cctools support."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--host-build', type=Path, default=ROOT/'work/host-tools-cxx-bss')
p.add_argument('--output', type=Path, default=ROOT/'work/build/shared-tools')
p.add_argument('--source-cache', type=Path, help='Optional local repository containing the pinned upstream commit')
a = p.parse_args()
b, host = a.output.resolve(), a.host_build.resolve()
if b.exists():p.error('Use a new output directory')
lock = json.loads((ROOT/'toolchain/fixed-vm/sources.json').read_text())
host_record = json.loads((host/'build-record.json').read_text())
expected_host = json.loads((ROOT/'toolchain/sources.json').read_text())
patch_root=ROOT/'toolchain/patches'
expected_patches={n:digest(patch_root/n) for n in (patch_root/'series').read_text().splitlines() if n and not n.startswith('#')}
if (host_record['status']!='passed' or host_record['sources']!=expected_host
        or host_record['patches_sha256']!=expected_patches):
    p.error('Host cctools build does not match the canonical source pins and patches')

upstream = ROOT/'work/upstream/cctools-622.9'
if not upstream.exists():
    upstream.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git','init','-q',str(upstream)],check=True)
    subprocess.run(['git','-C',str(upstream),'remote','add','origin',lock['url']],check=True)
if subprocess.check_output(['git','-C',str(upstream),'status','--porcelain']):
    p.error('Pinned source checkout has local changes')
if subprocess.run(['git','-C',str(upstream),'cat-file','-e',lock['revision']],capture_output=True).returncode:
    subprocess.run(['git','-C',str(upstream),'fetch','--depth=1',str(a.source_cache.resolve()) if a.source_cache else 'origin',lock['revision']],check=True)
subprocess.run(['git','-C',str(upstream),'checkout','-q','--detach',lock['revision']],check=True)
b.mkdir(parents=True)
s = b/'source'
# Export the exact Git tree rather than copying potentially untracked files.
with (b/'source.tar').open('wb') as f:
    subprocess.run(['git','-C',str(upstream),'archive',lock['revision']],stdout=f,check=True)
import tarfile
s.mkdir()
with tarfile.open(b/'source.tar') as f:f.extractall(s,filter='data')
patchdir = ROOT/'toolchain/fixed-vm/patches'
patches=[patchdir/n for n in (patchdir/'series').read_text().splitlines() if n and not n.startswith('#')]
for patch in patches:
    subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patch)],cwd=s,check=True,stdout=subprocess.DEVNULL)
# Use the current, pinned cctools headers/support library. This older component
# supplies mkshlib, which Apple removed from later releases.
headers=host/'source/include'
foreign=ROOT/'work/host-source-headers/cctools/include/foreign'
flags=['clang','-m32','-std=gnu11','-O2','-g0','-ffile-prefix-map='+str(ROOT)+'=SOURCE','-fcommon','-Dround=shlib_round',
       '-Wno-deprecated-declarations','-Werror=implicit-function-declaration',
       '-Werror=int-conversion','-Werror=incompatible-pointer-types','-Wno-format',
       '-Wno-constant-conversion','-DNEXTSTEP_CCTOOLS','-D_DARWIN_C_SOURCE',
       '-DMAP_RESILIENT_CODESIGN=0','-DCPU_TYPE_RISCV32=24','-DHAVE_BCMP',
       '-DHAVE_BZERO','-DHAVE_BCOPY','-DHAVE_INDEX','-DHAVE_RINDEX',
       '-D__LITTLE_ENDIAN__','-D__DARWIN_UNIX03=0',
       '-include',str(ROOT/'toolchain/compat/host.h'),'-I'+str(headers),
       '-I'+str(foreign),'-I'+str(s/'include'),'-I'+str(s/'mkshlib')]
steps=[]
def run(cmd):
    result=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
    (b/('step-'+str(len(steps))+'.log')).write_text(result.stdout+result.stderr)
    steps.append({'command':list(map(str,cmd)),'exitcode':result.returncode})
    if result.returncode:raise SystemExit(result.stderr)
objects=[]
for name in ['mkshlib/mkshlib.c','mkshlib/target.c','mkshlib/host.c','mkshlib/errors.c','mkshlib/parse_spec.c','libstuff/round.c']:
    obj=b/(Path(name).stem+'.o');run(flags+['-c',s/name,'-o',obj]);objects.append(obj)
(b/'bin').mkdir()
run(['clang','-m32','-o',b/'bin/mkshlib',*objects,host/'libstuff.a'])
record={'schema':1,'status':'passed','sources':lock,'patches_sha256':{p.name:digest(p) for p in patches},
        'host_build_record_sha256':digest(host/'build-record.json'),
        'host_support_sha256':digest(host/'libstuff.a'),'steps':steps,
        'mkshlib_sha256':digest(b/'bin/mkshlib')}
(b/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
print('Built pinned fixed-VM tools in '+str(b))
