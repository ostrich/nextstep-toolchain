#!/usr/bin/env python3
"""Run the focused threading probe in an isolated OPENSTEP test guest."""
import argparse
import importlib.util
import json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ['build','agent-client','socket']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--runtime',type=Path)
a=p.parse_args()
s=importlib.util.spec_from_file_location('agent',a.agent_client);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
paths={'/private/tmp/ns33-thread-subset-test':a.build/'threads'}
if a.runtime:paths['/usr/local/lib/libnextstepcompat.1.shlib']=a.runtime
results=[];owned=[]
try:
 with m.GuestAgent(str(a.socket.resolve()),15) as g:
  for name in paths:
   v=g.execute('/bin/sh',['-c','if test -f "$1" || test -d "$1"; then echo EXISTS; else echo ABSENT; fi','check',name])
   assert v['stdout'].strip()==b'ABSENT',(name,v)
  for name,source in paths.items():g.upload(source,name,mode=0o755);owned.append(name)
  v=g.execute('/private/tmp/ns33-thread-subset-test',[],execution_timeout=60)
  results.append({k:(x.decode(errors='replace') if isinstance(x,bytes) else x) for k,x in v.items()})
  assert v['exitcode']==0 and b'PASS threading subset:' in v['stdout'],v
  print(v['stdout'].decode(),end='')
finally:
 if owned:
  with m.GuestAgent(str(a.socket.resolve()),15) as g:assert g.execute('/bin/rm',['-f']+owned)['exitcode']==0
 (a.build/'openstep-validation.json').write_text(json.dumps(results,indent=2)+'\n')
