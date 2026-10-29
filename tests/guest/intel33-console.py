#!/usr/bin/env python3
"""Bounded QMP keyboard and console checks for a prepared Intel NS3.3 lab."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import runpy
import time
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--lab', type=Path, required=True)
p.add_argument('--console-client', type=Path, required=True,
               help='Python console-control module exposing Guest')
p.add_argument('action', choices=['shot', 'wait', 'type', 'halt-state'])
p.add_argument('value', nargs='?', default='current')
p.add_argument('--expect', help='Require this console regex before typing')
p.add_argument('--timeout', type=int, default=120)
a = p.parse_args()
if not a.console_client.is_file():
    p.error('--console-client must name an existing Python module')
from PIL import Image
Guest = runpy.run_path(str(a.console_client))['Guest']
g = Guest(a.lab)
def screen(name='current'):
    path = g.screen(name)
    ocr = g.directory / (name + '-ocr.png')
    with Image.open(path) as im:
        im.convert('L').resize((im.width * 2, im.height * 2)).save(ocr)
    result = subprocess.run(['tesseract', str(ocr), 'stdout', '--psm', '6'],
                            capture_output=True, text=True, check=True, timeout=10)
    (g.directory / (name + '.txt')).write_text(result.stdout)
    return result.stdout
if a.action == 'shot':
    print(screen(a.value))
elif a.action == 'wait':
    if not 0 < a.timeout <= 600:
        p.error('Timeout must be between 1 and 600 seconds')
    deadline = time.monotonic() + a.timeout
    while True:
        text = screen('readiness')
        if re.search(a.value, text, re.I):
            print(text)
            break
        if time.monotonic() >= deadline:
            raise SystemExit('Console readiness timed out; inspect readiness.png')
        time.sleep(2)
elif a.action == 'type':
    if a.expect and not re.search(a.expect, screen('before-input'), re.I):
        raise SystemExit('Unexpected console; inspect before-input.png')
    names = {' ': 'spc', '\n': 'ret', '\t': 'tab', ',': 'comma', '.': 'dot',
             '/': 'slash', ':': 'shift-semicolon', ';': 'semicolon', '-': 'minus',
             '_': 'shift-minus', '=': 'equal', '+': 'shift-equal',
             '\\': 'backslash', '|': 'shift-backslash', '"': 'shift-apostrophe',
             "'": 'apostrophe', '>': 'shift-dot', '<': 'shift-comma',
             '$': 'shift-4', '?': 'shift-slash', '&': 'shift-7', '*': 'shift-8',
             '(': 'shift-9', ')': 'shift-0', '[': 'bracket_left', ']': 'bracket_right'}
    if len(a.value) > 1024 or any(c not in names and
        (not c.isascii() or not c.isalnum()) for c in a.value):
        p.error('Unsupported key or overly long input')
    for char in a.value:
        key = names.get(char, 'shift-' + char.lower() if char.isupper() else char)
        result = g.qmp('human-monitor-command', {'command-line': 'sendkey ' + key + ' 30'})
        if result:
            raise SystemExit('Keyboard command failed: ' + str(result))
        time.sleep(.08)
    print('Sent paced input to the prepared VM console.')
else:
    status = g.qmp('query-status')
    registers = g.qmp('human-monitor-command', {'command-line': 'info registers'})
    (g.directory / 'halt-state.json').write_text(json.dumps(status, indent=2) + '\n')
    (g.directory / 'halt-registers.txt').write_text(registers)
    print(status)
    print(registers)
