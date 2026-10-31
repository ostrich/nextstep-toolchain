#!/usr/bin/env python3
"""Build four languages and a threaded C++ executable for every NeXT target."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
tc, sdk, out = a.toolchain.resolve(), a.sdk.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
sources = {
    'c': '#include <stdio.h>\nint main(void){return puts("host qualification")<0;}\n',
    'cc': '#include <cstdio>\n#include <thread>\n#include <atomic>\n#include <stdexcept>\n'
          'int main(){std::atomic<int> n(0);std::thread t([&]{++n;});t.join();'
          'try{throw std::runtime_error("ok");}catch(const std::exception &e){'
          'return n!=1 || e.what()[0]!=111;}return 2;}\n',
    'm': '@interface Probe { int number; } - (int)value; @end\n'
         '@implementation Probe - (int)value {return number;} @end\n'
         'int main(void){return 0;}\n',
    'mm': '@interface Probe { int number; } - (int)value; @end\n'
          '@implementation Probe - (int)value {return number;} @end\n'
          'template<class T>T twice(T n){return n+n;}\n'
          'int main(){return twice(3)!=6;}\n',
}
for suffix, source in sources.items():
    (out / ('probe.' + suffix)).write_text(source)

def build(arch):
    rows = []
    for suffix in sources:
        name = arch + '-' + suffix
        command = [str(tc/'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch,
                   '-O2', '-g0', 'probe.' + suffix, '-o', name]
        r = subprocess.run(command, cwd=out, capture_output=True)
        (out/(name+'.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:
            raise RuntimeError(name + ': ' + r.stderr.decode(errors='replace'))
        rows.append((name, hashlib.sha256((out/name).read_bytes()).hexdigest()))
    return rows
with ThreadPoolExecutor(4) as pool:
    results = dict(row for batch in pool.map(build, ['i386','m68k','hppa','sparc']) for row in batch)
for suffix in sources:
    name = 'fat-' + suffix
    subprocess.run([str(tc/'bin/nextstep-lipo'), '-create',
                    *[str(out/(arch+'-'+suffix)) for arch in ['i386','m68k','hppa','sparc']],
                    '-output',str(out/name)],check=True)
    results[name] = hashlib.sha256((out/name).read_bytes()).hexdigest()
(out/'results.json').write_text(json.dumps({'passed':True,'executables':results},indent=2)+'\n')
print('PASS: 16 thin and four fat C/C++/Objective-C/Objective-C++ executables built')
