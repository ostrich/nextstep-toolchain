#!/usr/bin/env python3
"""Runtime loading checks; use only an authorized isolated test guest."""
import argparse
import importlib.util,json
from pathlib import Path
p=argparse.ArgumentParser(description='Validate diamond loading in an isolated OPENSTEP guest')
p.add_argument('--agent-client',type=Path,required=True)
p.add_argument('--socket',type=Path,required=True)
p.add_argument('--build',type=Path,required=True)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('agent',a.agent_client)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r=a.build.resolve()
results=[];installed=[]
with m.GuestAgent(str(a.socket.resolve()),15) as g:
 def execute(path,args):
  v=g.execute(path,args,execution_timeout=30)
  results.append({'path':path,'args':args,**{k:(x.decode(errors='replace') if isinstance(x,bytes) else x) for k,x in v.items()}})
  return v
 paths=['/usr/local/lib/libdep'+name+'.1.shlib' for name in ['leaf','left','right','top']]+['/private/tmp/shared-dependency-consumer']
 for path in paths:
  v=execute('/bin/sh',['-c','if test -f "$1"; then echo EXISTS; else echo ABSENT; fi','check',path])
  assert v['stdout'].strip()==b'ABSENT',(path,v)
 try:
  for path in paths:
   source=r/('consumer' if path.endswith('consumer') else Path(path).name)
   g.upload(source,path,mode=0o755);installed.append(path)
  directory='/private/tmp/shared-dependency-test'
  v=execute('/bin/mkdir',[directory]);assert v['exitcode']==0,v
  installed.append(directory)
  for name in ['consumer','require2','leaf-upgrade.shlib','run-dependencies.sh']:
   g.upload(r/name,directory+'/'+name,mode=0o755)
  v=execute('/bin/sh',[directory+'/run-dependencies.sh',directory])
  assert v['exitcode']==0 and b'PASS dependency batch complete' in v['stdout'],v
  print(v['stdout'].decode(),end='')
 finally:
  # Launch errors can close the agent connection. Reconnect for cleanup so
  # an expected loader failure cannot leave test libraries in the guest.
  try:
   g.__exit__(None,None,None)
   with m.GuestAgent(str(a.socket.resolve()),15) as cleanup:
    if installed:
     v=cleanup.execute('/bin/rm',['-rf']+installed,execution_timeout=30)
     assert v['exitcode']==0,v
  finally:
   (r/'openstep-validation.json').write_text(json.dumps(results,indent=2)+'\n')
