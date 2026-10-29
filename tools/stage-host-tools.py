#!/usr/bin/env python3
"""Stage verified host-tool updates without rebuilding unrelated target runtimes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from build_inputs import digest
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base',type=Path,default=ROOT/'install/current')
p.add_argument('--build',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();base=a.base.resolve();build=a.build.resolve();out=a.output.resolve()
if out.exists() or out.is_relative_to(base) or (ROOT/'install/snapshots').resolve() in out.parents:
 p.error('Use a fresh staging directory outside installed bundles')
r=json.loads((build/'build-record.json').read_text());manifest=json.loads((base/'toolchain.json').read_text())
patchdir=ROOT/'toolchain/patches'
hashes={n:digest(patchdir/n) for n in (patchdir/'series').read_text().splitlines() if n and not n.startswith('#')}
if r.get('status')!='passed' or any(s['exitcode'] for s in r['commands']):p.error('Require a successful host-tools build')
if r['sources']!=json.loads((ROOT/'toolchain/sources.json').read_text()) or r['patches_sha256']!=hashes:p.error('Host-tools source pins or patches changed')
for name,value in r['compatibility_sha256'].items():
 if digest(ROOT/'toolchain/compat'/name)!=value:p.error('Host compatibility sources changed')
for name,value in r['binaries_sha256'].items():
 if digest(build/'bin'/name)!=value:p.error('Host-tool binary changed: '+name)
for name,value in manifest['files'].items():
 if digest(base/name)!=value:p.error('Base bundle file changed: '+name)
for name,value in manifest['symlinks'].items():
 if not (base/name).is_symlink() or os.readlink(base/name)!=value:p.error('Base bundle symlink changed: '+name)
shutil.copytree(base,out,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['as-i386','as-m68k','as-sparc','as-hppa','ld','lipo','libtool','nm','ar','strip']:
 relative='libexec/cctools/'+name;target=out/relative
 shutil.copy2(build/'bin'/name,target)
 if manifest.get('host_binaries_stripped'):subprocess.run(['strip','--strip-unneeded',str(target)],check=True)
 manifest['files'][relative]=digest(target)
for field,key in [('host_tools','sources'),('host_tools_patch_sha256','patch_sha256'),('host_tools_patches_sha256','patches_sha256'),('host_compatibility_sha256','compatibility_sha256')]:manifest[field]=r[key]
manifest['host_tools_build_record_sha256']=digest(build/'build-record.json')
(out/'toolchain.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Staged verified host tools; execute regressions before promotion')
