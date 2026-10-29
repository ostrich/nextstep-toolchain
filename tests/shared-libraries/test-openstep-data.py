#!/usr/bin/env python3
"""Check data exports and a compatible upgrade in an isolated OPENSTEP guest."""
import argparse
import importlib.util
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['build','agent-client','socket']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();root=a.build.resolve()
spec=importlib.util.spec_from_file_location('agent',a.agent_client)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
paths=['/usr/local/lib/libdatatest.1.shlib','/private/tmp/shared-data-consumer']
owned=[];results=[]
try:
 with m.GuestAgent(str(a.socket.resolve()),15) as g:
  for path in paths:
   v=g.execute('/bin/sh',['-c','if test -f "$1" || test -d "$1"; then echo EXISTS; else echo ABSENT; fi','check',path])
   assert v['stdout'].strip()==b'ABSENT',(path,v)
  g.upload(root/'consumer',paths[1],mode=0o755);owned.append(paths[1])
  for version in [1,2]:
   g.upload(root/str(version)/'libdatatest.1.shlib',paths[0],mode=0o755)
   if paths[0] not in owned:owned.append(paths[0])
   v=g.execute(paths[1],[],execution_timeout=30)
   results.append({'version':version,**{k:(x.decode(errors='replace') if isinstance(x,bytes) else x) for k,x in v.items()}})
   expected='data ABI callback '+str(11 if version==1 else 111)
   assert v['exitcode']==0 and expected.encode() in v['stdout'],v
   print('PASS OPENSTEP public data runtime version',version,flush=True)
finally:
 if owned:
  with m.GuestAgent(str(a.socket.resolve()),15) as g:
   assert g.execute('/bin/rm',['-f']+owned)['exitcode']==0
 (root/'openstep-validation.json').write_text(json.dumps(results,indent=2)+'\n')
