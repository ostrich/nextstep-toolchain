#!/usr/bin/env python3
"""Capture the unmodified release's target-support baseline."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def main():
    version = json.loads((ROOT / 'sources.lock.json').read_text())['gcc']['version']
    source = ROOT / 'work/pristine' / ('gcc-' + version)
    build = ROOT / 'work/configure-baseline'
    build.mkdir(parents=True, exist_ok=True)
    configure = [str(source / 'configure'), '--target=i386-next-nextstep3.3',
                 '--disable-bootstrap', '--disable-multilib', '--disable-nls',
                 '--enable-languages=c,c++,objc,obj-c++', '--without-headers']
    env = dict(os.environ, LC_ALL='C')
    results = {}
    for name, command in [('configure', configure),
                          ('configure-gcc', ['make', '-j4', 'configure-gcc'])]:
        with (build / (name + '.log')).open('wb') as log:
            result = subprocess.run(command, cwd=build, env=env, stdout=log,
                                    stderr=subprocess.STDOUT)
        results[name] = {'command': command, 'exit_code': result.returncode}
        print(f'{name}: exit {result.returncode}; see {build.name}/{name}.log', flush=True)
        if result.returncode:
            break
    (build / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print('Review logs: failure alone does not identify its cause.')

if __name__ == '__main__':
    main()
