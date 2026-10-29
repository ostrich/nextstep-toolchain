#!/usr/bin/env python3
"""Run IPv4 adapters in an isolated, configured OPENSTEP guest."""
import argparse
import importlib.util
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['build','agent-client','socket']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--runtime',type=Path)
a=p.parse_args()
s=importlib.util.spec_from_file_location('agent',a.agent_client);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
probes=json.loads((a.build/'build-record.json').read_text())['probes_sha256']
paths={'/private/tmp/ns33-'+name:a.build/name for name in probes}
if a.runtime:paths['/usr/local/lib/libnextstepcompat.1.shlib']=a.runtime
results=[];owned=[]
try:
 with m.GuestAgent(str(a.socket.resolve()),15) as g:
  for name in paths:
   v=g.execute('/bin/sh',['-c','if test -f "$1" || test -d "$1"; then echo EXISTS; else echo ABSENT; fi','check',name])
   assert v['stdout'].strip()==b'ABSENT',(name,v)
  for name,source in paths.items():g.upload(source,name,mode=0o755);owned.append(name)
  for name in probes:
   args=['--native-databases'] if name=='network' else []
   v=g.execute('/private/tmp/ns33-'+name,args,execution_timeout=60)
   results.append({'probe':name,**{k:(x.decode(errors='replace') if isinstance(x,bytes) else x) for k,x in v.items()}})
   assert v['exitcode']==0 and b'0 failures' in v['stdout'],v
   print(name+': '+v['stdout'].decode(),end='')
finally:
 if owned:
  with m.GuestAgent(str(a.socket.resolve()),15) as g:assert g.execute('/bin/rm',['-f']+owned)['exitcode']==0
 (a.build/'openstep-validation.json').write_text(json.dumps(results,indent=2)+'\n')
