#!/usr/bin/env python3
"""Verify executable-relative debug objects after moving a real linked program."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--gdb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('debug_bundle', ROOT / 'tools/nextstep-debug.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    original = output / 'original'
    original.mkdir()
    binary = original / 'program'
    shutil.copy2(args.binary, binary)
    source_debug = args.binary.with_name(args.binary.name + '.debug')
    copied_debug = original / source_debug.name
    if source_debug.is_dir():
        shutil.copytree(source_debug, copied_debug)
    manifest = helper.bundle(binary, original / 'program.debug', 'program.debug')
    if copied_debug.is_dir() and copied_debug.name != 'program.debug':
        shutil.rmtree(copied_debug)
    moved = output / 'moved'
    original.rename(moved)
    command = [str(args.gdb.resolve()), '-q', '-nx', '-batch', '-ex', 'set auto-load off',
               '-ex', 'file ' + str(moved / 'program'), '-ex', 'info line compute',
               '-ex', 'ptype struct sample', '-ex', 'info address debugger_result']
    result = subprocess.run(command, cwd='/', capture_output=True, timeout=60)
    text = result.stdout + result.stderr
    (output / 'gdb.log').write_bytes(text)
    if (result.returncode or b'Line ' not in text or b'int count;' not in text
            or b'double value;' not in text or b'No line' in text):
        raise SystemExit('Relocated debug object reading failed; inspect gdb.log')
    # A malformed input must not be replaced or create an object directory.
    invalid = output / 'invalid'
    invalid.write_bytes(b'not an executable')
    try:
        helper.bundle(invalid, output / 'invalid.debug', 'invalid.debug')
    except ValueError:
        pass
    else:
        raise SystemExit('Malformed input was accepted')
    if invalid.read_bytes() != b'not an executable' or (output / 'invalid.debug').exists():
        raise SystemExit('Malformed-input failure changed output state')
    # A content-addressed object with incorrect contents must not be reused.
    retained = next((moved / 'program.debug').glob('*.o'))
    retained.write_bytes(b'tampered')
    # Preserve its timestamp so this exercises the content check, not mtime.
    os.utime(retained, (manifest['objects'][retained.name]['mtime'],) * 2)
    before = (moved / 'program').read_bytes()
    try:
        helper.bundle(moved / 'program', moved / 'program.debug', 'program.debug')
    except ValueError as error:
        if 'Content-addressed source object has changed' not in str(error):
            raise SystemExit('Integrity test failed for the wrong reason: ' + str(error))
    else:
        raise SystemExit('Modified object was accepted')
    # The filename must also match the content before retaining it as a source.
    if (moved / 'program').read_bytes() != before:
        raise SystemExit('Failed integrity check replaced the executable')
    (output / 'results.json').write_text(json.dumps({'passed': True, 'command': command,
        'manifest': manifest}, indent=2) + '\n')
    print('Relocation, malformed input and retained-object integrity: PASS')


if __name__ == '__main__':
    main()
