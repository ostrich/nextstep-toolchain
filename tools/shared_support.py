"""Install verified shared-library construction tools into an unpromoted bundle."""
import json
from pathlib import Path
import shutil
import subprocess
from build_inputs import digest
ROOT=Path(__file__).resolve().parents[1]
def install(prefix, build):
    prefix,build=Path(prefix).resolve(),Path(build).resolve()
    if (ROOT/'install/snapshots').resolve() in prefix.parents:
        raise ValueError('Cannot modify an installed snapshot')
    record=json.loads((build/'build-record.json').read_text())
    lock=json.loads((ROOT/'toolchain/fixed-vm/sources.json').read_text())
    patchdir=ROOT/'toolchain/fixed-vm/patches'
    hashes={n:digest(patchdir/n) for n in (patchdir/'series').read_text().splitlines() if n and not n.startswith('#')}
    if (record['status']!='passed' or record['sources']!=lock or record['patches_sha256']!=hashes
            or any(x['exitcode'] for x in record['steps'])
            or digest(build/'bin/mkshlib')!=record['mkshlib_sha256']):
        raise ValueError('Shared tools do not match current pinned sources and patches')
    manifest=json.loads((prefix/'toolchain.json').read_text())
    for source,name in [(build/'bin/mkshlib','libexec/cctools/mkshlib'),
                         (ROOT/'tools/nextstep-shlib','bin/nextstep-shlib'),
                         (ROOT/'tools/nextstep-gcc','bin/nextstep-gcc')]:
        dest=prefix/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);dest.chmod(0o755)
        if name.endswith('/mkshlib'):subprocess.run(['strip','--strip-unneeded',str(dest)],check=True)
        manifest['files'][name]=digest(dest)
    licenses=prefix/'share/licenses/cctools-fixed-vm'
    licenses.mkdir(parents=True,exist_ok=True)
    shutil.copy2(build/'source/APPLE_LICENSE',licenses/'APPLE_LICENSE')
    notice=(build/'source/libstuff/round.c').read_text().split('#include',1)[0]
    (licenses/'ROUND-NOTICE.txt').write_text(notice)
    for path in licenses.iterdir():
        path.chmod(0o644);manifest['files'][str(path.relative_to(prefix))]=digest(path)
    manifest['fixed_vm_tools']={'sources':lock,'patches_sha256':hashes,
                                'build_record_sha256':digest(build/'build-record.json'),
                                'wrappers_sha256':{name:digest(ROOT/'tools'/name) for name in ['nextstep-gcc','nextstep-shlib']}}
    manifest['capabilities']={'shared_libraries':['fixed-vm-function-exports','fixed-vm-transitive-imports','fixed-vm-abi-reservations','fixed-vm-canonical-function-entries']}
    (prefix/'toolchain.json').write_text(json.dumps(manifest,indent=2)+'\n')
