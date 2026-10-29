#!/usr/bin/env python3
"""Run shared compatibility regressions in an isolated OPENSTEP guest."""
import argparse
import importlib.util
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['agent-client','socket','shared','tests']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('agent',a.agent_client)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
probes=json.loads((a.tests/'build-record.json').read_text())['artifacts']
library='/usr/local/lib/libnextstepcompat.1.shlib';directory='/private/tmp/shared-compat-regressions'
results={};owned=[]
with m.GuestAgent(str(a.socket.resolve()),15) as g:
 for path,kind in [(library,'-f'),(directory,'-d')]:
  v=g.execute('/bin/sh',['-c','if test '+kind+' "$1"; then echo EXISTS; else echo ABSENT; fi','check',path])
  assert v['stdout'].strip()==b'ABSENT',(path,v)
 try:
  g.upload(a.shared/'libnextstepcompat.1.shlib',library,mode=0o755);owned.append(library)
  assert g.execute('/bin/mkdir',[directory])['exitcode']==0
  owned.append(directory)
  for name in probes:
   g.upload(a.tests/name,directory+'/'+name,mode=0o755)
   v=g.execute('/bin/sh',['-c','cd "$1" && exec "./$2" "$1"','test',directory,name],execution_timeout=120)
   results[name]={k:(x.decode(errors='replace') if isinstance(x,bytes) else x) for k,x in v.items()}
   assert v['exitcode']==0,(name,results[name])
   print('PASS OPENSTEP shared '+name,flush=True)
 finally:
  g.close()
  try:
   with m.GuestAgent(str(a.socket.resolve()),15) as clean:
    if owned:assert clean.execute('/bin/rm',['-rf']+owned)['exitcode']==0
  finally:
   (a.tests/'openstep-results.json').write_text(json.dumps(results,indent=2)+'\n')
