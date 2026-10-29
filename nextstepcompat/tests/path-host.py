#!/usr/bin/env python3
"""Compare reentrant path adapters with host libc and check CWD preservation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import errno
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['cc', '-O2', '-std=gnu11', '-shared', '-fPIC',
    '-Dgetcwd=nextstep_getcwd', str(ROOT / 'src/path-compat.c'),
    '-o', str(out / 'path.so')], check=True)
port = ctypes.CDLL(str(out / 'path.so'), use_errno=True)
libc = ctypes.CDLL(None, use_errno=True)
for f in [port.ns33_realpath, libc.realpath]:
    f.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    f.restype = ctypes.c_void_p
port.nextstep_getcwd.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
port.nextstep_getcwd.restype = ctypes.c_void_p
libc.free.argtypes = [ctypes.c_void_p]
root = out / 'tree'
(root / 'a/b').mkdir(parents=True, exist_ok=True)
(root / 'a/b/file').write_text('test')
for name, target in [('link', 'a/b'), ('abs', str(root / 'a/b')),
                     ('cycle-a', 'cycle-b'), ('cycle-b', 'cycle-a'), ('dangling', 'absent')]:
    path = root / name
    if not path.is_symlink():
        path.symlink_to(target)
previous = Path.cwd()
os.chdir(root)
def resolve(function, path):
    ctypes.set_errno(0)
    pointer = function(os.fsencode(path), None)
    result = (ctypes.string_at(pointer) if pointer else None,
              0 if pointer else ctypes.get_errno())
    if pointer:
        libc.free(pointer)
    return result
cases = ['.', '..', 'a', 'a/b/file', 'a/b/../b/file', 'link/file', 'abs/file',
         'abs/../b/file', 'a/b/file/', 'a/b/file/..', 'absent', 'dangling',
         'cycle-a', '', '/', '/../..', str(root / 'link/file')]
checks = 0
try:
    reference = {path: resolve(libc.realpath, path) for path in cases}
    def check_path(path):
        result = resolve(port.ns33_realpath, path)
        if result != reference[path] or Path.cwd() != root:
            raise RuntimeError(repr((path, result, reference[path])))
    for path in cases:
        check_path(path)
        checks += 1
    for size in [0, 1, 1024, 4096]:
        ctypes.set_errno(0)
        pointer = port.nextstep_getcwd(None, size)
        if size == 1:
            assert not pointer and ctypes.get_errno() == errno.ERANGE
        else:
            assert pointer and os.fsdecode(ctypes.string_at(pointer)) == str(root)
            libc.free(pointer)
        checks += 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check_path, cases * 20))
    checks += len(cases) * 20
finally:
    os.chdir(previous)
(out / 'results.json').write_text(json.dumps({'checks': checks, 'failures': 0,
    'concurrent_path_calls': len(cases) * 20, 'cwd_preserved': True}, indent=2) + '\n')
print('Path checks passed:', checks)
