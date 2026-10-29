#!/usr/bin/env python3
"""Build positive/negative controls for an owned NEXTSTEP 68k guest batch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'watchdog', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
fixed = p.add_mutually_exclusive_group(required=True)
fixed.add_argument('--candidate', type=Path, help='Uninstalled compiler build')
fixed.add_argument('--fixed-toolchain', type=Path, help='Complete staged or installed fixed bundle')
a = p.parse_args()
tc = a.toolchain.resolve(strict=True)
sdk = a.sdk.resolve(strict=True)
candidate = a.candidate.resolve(strict=True) if a.candidate else None
fixed_tc = a.fixed_toolchain.resolve(strict=True) if a.fixed_toolchain else None
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
payload = out / 'payload'
payload.mkdir()
sources = [Path(__file__).resolve().parent / name for name in ['layout.c', 'check.c']]
commands = []
for name in ['old', 'disabled', 'fixed']:
    driver = ((fixed_tc / 'bin/nextstep-gcc' if fixed_tc else ROOT / 'tools/nextstep-gcc')
              if name == 'fixed' else tc / 'bin/nextstep-gcc')
    command = [str(driver), '--sdk', str(sdk), '-arch', 'm68k', '-O2']
    if name == 'disabled':
        command += ['-fno-caller-saves']
    if name == 'fixed' and candidate:
        command += ['--compiler-build', str(candidate), '--host-tools', str(tc / 'libexec/cctools')]
    command += [*map(str, sources), '-o', str(payload / name)]
    subprocess.run(command, check=True)
    commands.append(command)
for source in sources:
    shutil.copy2(source, payload / source.name)
shutil.copy2(Path(__file__).with_name('run.sh'), payload / 'run.sh')
shutil.copy2(a.watchdog.resolve(strict=True), payload / 'watchdog')
(out / 'inputs.json').write_text(json.dumps({
    'commands': commands,
    'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    'binary_sha256': {name: hashlib.sha256((payload / name).read_bytes()).hexdigest()
                      for name in ['old', 'disabled', 'fixed']},
    'candidate_record': json.loads((candidate / 'build-record.json').read_text()) if candidate else None,
    'fixed_manifest_sha256': hashlib.sha256((fixed_tc / 'toolchain.json').read_bytes()).hexdigest() if fixed_tc else None,
    'canonical_manifest_sha256': hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest()
}, indent=2) + '\n')
print(payload)
