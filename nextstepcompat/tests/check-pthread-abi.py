#!/usr/bin/env python3
"""Verify unchanged absolute import addresses on all four supported targets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
for name in ['toolchain','old-import','new-import','output']:
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
nm=a.toolchain.resolve()/'libexec/cctools/nm'
record={'old_sha256':hashlib.sha256(a.old_import.read_bytes()).hexdigest(),
        'new_sha256':hashlib.sha256(a.new_import.read_bytes()).hexdigest(), 'architectures':{}}
for arch in ['m68k','i386','hppa','sparc']:
    def symbols(path):
        text=subprocess.check_output([str(nm),'-arch',arch,'-g',str(path)],text=True)
        return {fields[2]:fields[0] for line in text.splitlines()
                if len(fields:=line.split())==3 and fields[1]=='A'}
    old,new=symbols(a.old_import),symbols(a.new_import)
    if not old or any(new.get(name)!=value for name,value in old.items()):
        raise SystemExit('Changed existing shared import address: '+arch)
    record['architectures'][arch]={'preserved':len(old),'appended':len(new)-len(old)}
a.output.write_text(json.dumps(record,indent=2)+'\n')
print('PASS unchanged shared import addresses on NIHS')
