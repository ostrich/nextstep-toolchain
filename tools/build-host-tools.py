#!/usr/bin/env python3
"""Build pinned Apple classic Mach-O tools on Linux, without guest tools."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--jobs', type=int, default=8)
p.add_argument('--cc', default='clang')
p.add_argument('--output', type=Path, default=ROOT / 'work/host-tools')
a = p.parse_args()
if sys.platform != 'linux':
    p.error('This host portability layer currently targets Linux')
if a.jobs < 1:
    p.error('--jobs must be positive')
B = a.output.resolve()
B.mkdir(parents=True, exist_ok=True)
lock = json.loads((ROOT / 'toolchain/sources.json').read_text())

def git_checkout(name, entry):
    d = ROOT / 'work' / ('host-source-' + name)
    if not d.exists():
        subprocess.run(['git', 'init', '-q', str(d)], check=True)
        subprocess.run(['git', '-C', str(d), 'remote', 'add', 'origin', entry['url']], check=True)
    if subprocess.check_output(['git', '-C', str(d), 'status', '--porcelain']):
        raise SystemExit('Source checkout has local changes: ' + str(d))
    found = subprocess.run(['git', '-C', str(d), 'cat-file', '-e', entry['revision']], capture_output=True)
    if found.returncode:
        subprocess.run(['git', '-C', str(d), 'fetch', '--depth=1', 'origin', entry['revision']], check=True)
    subprocess.run(['git', '-C', str(d), 'checkout', '-q', '--detach', entry['revision']], check=True)
    return d

original = git_checkout('apple', lock['apple_cctools'])
foreign = git_checkout('headers', lock['foreign_headers']) / lock['foreign_headers']['subdirectory']
patch = ROOT / 'toolchain/patches/0001-linux-host-and-nextstep-formats.patch'
# Build in a fresh prepared source directory. The pinned checkout stays untouched.
S = B / 'source'
if S.exists():
    shutil.rmtree(S)
shutil.copytree(original, S, ignore=shutil.ignore_patterns('.git'))
patches = [ROOT / 'toolchain/patches' / name for name in
           (ROOT / 'toolchain/patches/series').read_text().splitlines()
           if name and not name.startswith('#')]
for item in patches:
    subprocess.run(['patch', '-p1', '--fuzz=0', '-i', str(item)], cwd=S,
                   check=True, stdout=subprocess.DEVNULL)
# Apple exports this header as mach/machine.h in its installed SDK.
shutil.copyfile(S / 'include/mach/machine-cctools.h', S / 'include/mach/machine.h')
flags = [a.cc, '-m32', '-std=gnu11', '-O2', '-g0', '-ffile-prefix-map=' + str(ROOT) + '=SOURCE', '-fcommon',
         '-Wno-deprecated-declarations', '-Werror=implicit-function-declaration',
         '-Werror=int-conversion', '-Werror=incompatible-pointer-types', '-Wno-format',
         '-Wno-constant-conversion', '-Wno-unused-command-line-argument',
         '-DNEXTSTEP_CCTOOLS', '-D_DARWIN_C_SOURCE', '-DMAP_RESILIENT_CODESIGN=0', '-DCPU_TYPE_RISCV32=24',
         '-DHAVE_BCMP', '-DHAVE_BZERO', '-DHAVE_BCOPY', '-DHAVE_INDEX', '-DHAVE_RINDEX',
         '-D__LITTLE_ENDIAN__', '-D__DARWIN_UNIX03=0',
         '-include', str(ROOT / 'toolchain/compat/host.h'),
         '-I' + str(S / 'include'), '-I' + str(foreign)]
records = []

def command(cmd, log):
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(r.stdout + r.stderr)
    return {'command': cmd, 'exitcode': r.returncode, 'log': str(log.relative_to(B))}

def batch(files, directory, extra=()):
    directory.mkdir(parents=True, exist_ok=True)
    def compile_one(f):
        out = directory / (f.stem + '.o')
        return out, command(flags + list(extra) + ['-c', str(f), '-o', str(out)], directory / (f.stem + '.log'))
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        rows = list(pool.map(compile_one, files))
    records.extend(row for _, row in rows)
    failed = [row for _, row in rows if row['exitcode']]
    if failed:
        for row in failed:
            print((B / row['log']).read_text(), file=sys.stderr)
        raise RuntimeError('Compilation failed')
    return [str(out) for out, _ in rows]

def link(name, objects):
    bin_dir = B / 'bin'
    bin_dir.mkdir(exist_ok=True)
    row = command([a.cc, '-m32', '-o', str(bin_dir / name), *objects], B / (name + '-link.log'))
    records.append(row)
    if row['exitcode']:
        raise RuntimeError((B / row['log']).read_text())

try:
    names = '''align depinfo args get_toc_byte_sex diagnostics write64 allocate arch
arch_usage best_arch bytesex errors execute fatal_arch fatals get_arch_from_host
hash_string hppa rnd swap_headers set_arch_flag_name print ofile_error reloc
version_number macosx_deployment_target unix_standard_mode guess_short_name ofile
ofile_get_word symbol_list seg_addr_table breakout writeout checkout crc32'''.split()
    support = batch([S / 'libstuff' / (n + '.c') for n in names] + [ROOT / 'toolchain/compat/host.c'], B / 'support')
    lib = B / 'libstuff.a'
    lib.unlink(missing_ok=True)
    subprocess.run(['ar', 'rcs', str(lib), *support], check=True)
    common = '''app as atof-generic atof-ieee expr fixes flonum-const flonum-copy
flonum-mult frags hash hex-value input-file input-scrub layout messages obstack
read sections symbols write_object xmalloc dwarf2dbg'''.split()
    version = batch([S / 'libstuff/apple_version.c'], B / 'version')
    for arch, defs, more in [('i386', ['I386'], ['i386']),
                             ('m68k', ['M68K', 'BUILTIN_MMUS'], ['m68k']),
                             ('sparc', ['SPARC'], ['sparc']),
                             ('hppa', ['HPPA'], ['hppa', 'hppa-aux'])]:
        objects = batch([S / 'as' / (n + '.c') for n in common + more], B / ('as-' + arch),
                        ['-DNeXT_MOD', *('-D' + d for d in defs), '-I' + str(S / 'as')])
        link('as-' + arch, objects + version + [str(lib)])
        print('Built as-' + arch, flush=True)
    objects = batch(sorted(f for f in (S / 'ld').glob('*.c') if f.stem != 'rld'), B / 'ld',
                    ['-include', str(S / 'include/stuff/arch.h'),
                     '-include', str(S / 'include/stuff/macosx_deployment_target.h'), '-I' + str(S / 'ld')])
    link('ld', objects + version + [str(lib)])
    for tool in ['lipo', 'libtool', 'nm', 'strip']:
        objects = batch([S / 'misc' / (tool + '.c')], B / ('misc-' + tool))
        link(tool, objects + version + [str(lib)])
    objects = batch(sorted((S / 'ar').glob('*.c')), B / 'ar', ['-I' + str(S / 'ar'), '-Wformat', '-Werror=format'])
    link('ar', objects + [str(lib)])
    # libtool selects archive-index mode using its invocation name.
    ranlib = B / 'bin/ranlib'
    ranlib.unlink(missing_ok=True)
    ranlib.symlink_to('libtool')
    status = 'passed'
finally:
    record = {'sources': lock, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'patches_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in patches},
              'host_abi': 'Linux i386 (requires 32-bit libc)', 'optimization': '-O2',
              'commands': records, 'status': locals().get('status', 'failed'),
              'compatibility_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                                       for f in (ROOT / 'toolchain/compat').glob('*.[ch]')},
              'binaries_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                                  for f in (B / 'bin').glob('*') if f.is_file()}}
    (B / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
print('Built host tools in ' + str(B / 'bin'))
