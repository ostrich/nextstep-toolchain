#!/usr/bin/env python3
"""Assemble shared-import ordering and transitive-upgrade runtime tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','diamond','closure','compat','iconv','lzo','output']:
 p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();out=a.output.resolve();tc=a.toolchain.resolve()
if out.exists():p.error('Use a fresh output directory')
out.mkdir(parents=True)
assets={};libraries={}
arches=['m68k','i386','hppa','sparc']
for order in ['dependency-first','newest-first','search-dependency-first','search-newest-first']:
 target=out/order
 subprocess.run([str(tc/'libexec/cctools/lipo'),'-create',
  *[str(a.diamond.resolve()/(arch+'-'+order)) for arch in arches],'-output',str(target)],check=True)
 assets[order]=str(target)
for order in ['old-first','new-first','all-load-old-first','all-load-new-first']:assets['closure-'+order]=str(a.closure.resolve()/order)
assets['parent-old.shlib']=str(a.closure.resolve()/'parent-old/libfixtureparent.1.shlib')
for root,names in [(a.compat,['nextstepcompat.1']),(a.iconv,['iconv.1','charset.1']),(a.lzo,['lzo2.1'])]:
 for name in names:
  filename='lib'+name+'.shlib';libraries[filename]=str(root.resolve()/filename)
libraries['libfixtureparent.1.shlib']=str(a.closure.resolve()/'parent-new/libfixtureparent.1.shlib')
libraries['libfixturechild.1.shlib']=str(a.closure.resolve()/'child/libfixturechild.1.shlib')
script=out/'run-codecs.sh';script.write_text('''#!/bin/sh
cd "$1" || exit 90
directory=`/bin/pwd` || exit 90
child=/usr/local/lib/libfixturechild.1.shlib
parent=/usr/local/lib/libfixtureparent.1.shlib
cleanup() {
 saved_status=$?
 trap 0
 if test -f "$directory/child.saved"; then /bin/mv "$directory/child.saved" "$child"; fi
 if test -f "$directory/parent.saved"; then /bin/cp "$directory/parent.saved" "$parent"; fi
 exit "$saved_status"
}
trap cleanup 0
for program in dependency-first newest-first search-dependency-first search-newest-first closure-old-first closure-new-first closure-all-load-old-first closure-all-load-new-first; do
 ./$program || exit 1
 echo "PASS executable $program"
done
/bin/mv "$child" "$directory/child.saved" || exit 2
./closure-old-first > missing.log 2>&1
missing_status=$?
cat missing.log
test "$missing_status" != 0 || exit 3
/bin/mv "$directory/child.saved" "$child" || exit 4
if grep "closure value" missing.log >/dev/null; then exit 5; fi
echo 'PASS missing added transitive dependency'
/bin/cp "$parent" "$directory/parent.saved" || exit 6
/bin/cp parent-old.shlib "$parent" || exit 7
./closure-old-first > insufficient.log 2>&1
insufficient_status=$?
cat insufficient.log
test "$insufficient_status" != 0 || exit 8
/bin/cp "$directory/parent.saved" "$parent" || exit 9
/bin/rm "$directory/parent.saved"
if grep "closure value" insufficient.log >/dev/null; then exit 10; fi
echo 'PASS compatible upgrade requires highest minor'
trap 0
echo 'PASS executable import closure batch complete'
''');assets[script.name]=str(script)
suite={'libraries':libraries,'assets':assets,'entry':script.name,
 'success_marker':'PASS executable import closure batch complete',
 'sha256':{name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in {**libraries,**assets}.items()}}
(out/'suite.json').write_text(json.dumps(suite,indent=2)+'\n')
