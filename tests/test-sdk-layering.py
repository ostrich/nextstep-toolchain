#!/usr/bin/env python3
"""Check shared header policy, qualified SDK paths and standalone C89 helpers."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
for name in ['toolchain', 'sdk', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--host-cc', default='cc')
a = p.parse_args()
if a.jobs < 1:
    p.error('--jobs must be positive')
tc, sdk, out = [x.resolve() for x in [a.toolchain, a.sdk, a.output]]
out.mkdir(parents=True, exist_ok=False)
for name in ['ns33-feature-profile.h', 'ns33-fdset.h']:
    if (tc / 'include/nextstepcompat' / name).read_bytes() != (ROOT / 'nextstepcompat/include' / name).read_bytes():
        raise SystemExit('Stage the current shared header before testing: ' + name)
fixtures={
 'standards-canonical':'#include <standards.h>\n#if __STRICT_ANSI__ != 1\n#error wrong ANSI selector\n#endif\nint x;\n',
 'standards-qualified':'#include <ansi/standards.h>\n#if __STRICT_ANSI__ != 1\n#error wrong ANSI selector\n#endif\nint x;\n',
 'fdzero-canonical':'#include <sys/types.h>\nvoid zero(fd_set *p) { FD_ZERO(p); }\n',
 'fdzero-qualified':'#include <bsd/sys/types.h>\nvoid zero(fd_set *p) { FD_ZERO(p); }\n',
 'fdzero-qualified-then-canonical':'#include <bsd/sys/types.h>\n#include <sys/types.h>\nvoid zero(fd_set *p) { FD_ZERO(p); }\n',
 'signal-canonical':'#include <signal.h>\nvoid (*f(void))(int) { return SIG_ERR; }\n',
 'signal-qualified':'#include <ansi/signal.h>\nvoid (*f(void))(int) { return SIG_ERR; }\n',
 'signal-qualified-then-canonical':'#include <ansi/signal.h>\n#include <signal.h>\nvoid (*f(void))(int) { return SIG_ERR; }\n',
 'netdb-mixed':'#include <bsd/netdb.h>\n#include <netdb.h>\n#include <bsd/netdb.h>\nstruct addrinfo *f(void){return 0;}\n',
 'fcntl-mixed':'#include <bsd/sys/fcntl.h>\n#include <sys/fcntl.h>\n#include <fcntl.h>\nint (*p)(const char *,int,...)=open;\n',
 'kernel-canonical':'#define KERNEL 1\n#include <standards.h>\n#ifdef _POSIX_SOURCE\n#error kernel profile was changed\n#endif\nint x;\n',
 'kernel-qualified':'#define KERNEL 1\n#include <ansi/standards.h>\n#ifdef _POSIX_SOURCE\n#error kernel profile was changed\n#endif\nint x;\n',
}

for name, source in fixtures.items():
    (out / (name + '.c')).write_text(source)
cases = [(arch, standard, name) for arch in ['i386', 'm68k', 'hppa', 'sparc']
         for standard in ['gnu17', 'gnu23', 'gnu++17'] for name in fixtures]

def run(case):
    arch, standard, name = case
    command = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch,
               '-x', 'c++' if '++' in standard else 'c', '-std=' + standard,
               '-O2', '-S']
    if '++' not in standard:
        command += ['-Werror=implicit-function-declaration', '-Werror=incompatible-pointer-types']
    command += [str(out / (name + '.c')), '-o', str(out / (arch + '-' + standard + '-' + name + '.s'))]
    result = subprocess.run(command, capture_output=True, text=True)
    return dict(arch=arch, standard=standard, case=name, command=command,
                exitcode=result.returncode, stderr=result.stderr, passed=result.returncode == 0)

with ThreadPoolExecutor(a.jobs) as pool:
    rows = list(pool.map(run, cases))

# SDK syntax repairs must also work without the runtime's public wrappers.
overlay = out / 'sdk-overlay'
subprocess.run([sys.executable, str(tc / 'libexec/nextstep/prepare-sdk.py'),
                '--sdk', str(sdk), '--output', str(overlay)], check=True)
sdk_only = ['standards-canonical', 'standards-qualified', 'fdzero-canonical',
            'fdzero-qualified', 'signal-canonical', 'signal-qualified',
            'kernel-canonical', 'kernel-qualified']
def run_sdk_only(case):
    arch, standard, name = case
    gcc = tc / 'libexec/gcc' / arch
    command = [str(gcc / 'xgcc'), '-B' + str(gcc) + '/', '-D_NEXT_SOURCE',
               '-nostdinc', '-isystem', str(overlay), '-isystem', str(gcc / 'include')]
    for directory in ['usr/include', 'usr/include/ansi', 'usr/include/bsd']:
        command += ['-idirafter', str(sdk / directory)]
    command += ['-x', 'c++' if '++' in standard else 'c', '-std=' + standard, '-O2', '-S']
    if '++' not in standard:
        command += ['-Werror=implicit-function-declaration', '-Werror=incompatible-pointer-types']
    command += [str(out / (name + '.c')), '-o',
                str(out / ('sdk-only-' + arch + '-' + standard + '-' + name + '.s'))]
    result = subprocess.run(command, capture_output=True, text=True)
    return dict(arch=arch, standard=standard, case='SDK-only ' + name,
                command=command, stderr=result.stderr, passed=result.returncode == 0)
with ThreadPoolExecutor(a.jobs) as pool:
    rows += list(pool.map(run_sdk_only, [(arch, standard, name)
                 for arch in ['i386', 'm68k', 'hppa', 'sparc']
                 for standard in ['gnu17', 'gnu23', 'gnu++17'] for name in sdk_only]))

# Component rebuilding passes its own headers through the public driver.
command = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', 'i386',
           '--compat-headers', str(ROOT / 'nextstepcompat/include'),
           '-std=gnu23', '-S', str(out / 'fdzero-qualified.c'),
           '-o', str(out / 'explicit-component-headers.s')]
result = subprocess.run(command, capture_output=True, text=True)
rows.append(dict(case='public driver component-header override',
                 passed=result.returncode == 0, stderr=result.stderr))

# The portable replacement must link to native libc on every target even
# when the compiler cannot optimize memset into an inline sequence.
source = out / 'native-fdset.c'
source.write_text('#include <sys/types.h>\nint main(void) { fd_set set; '
                  'FD_SET(7, &set); FD_ZERO(&set); return FD_ISSET(7, &set) != 0; }\n')
for arch in ['i386', 'm68k', 'hppa', 'sparc']:
    command = [str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk), '-arch', arch,
               '-O2', '-fno-builtin', str(source), '-o', str(out / ('native-fdset-' + arch))]
    result = subprocess.run(command, capture_output=True, text=True)
    rows.append(dict(arch=arch, case='native FD_ZERO libc linkage',
                     passed=result.returncode == 0, stderr=result.stderr))

# Exercise the reusable helper without SDK adaptation or our cross compiler.
# Strict ISO C89 and disabled builtins ensure FD_ZERO uses native memset.
source = out / 'standalone.c'
source.write_text("""#include <ns33-feature-profile.h>
#ifndef _POSIX_SOURCE
#error application profile missing
#endif
typedef struct { unsigned char bytes[32]; } fd_set;
#define FD_ZERO(p) bzero((p), sizeof(*(p)))
#include <ns33-fdset.h>
#include <ns33-fdset.h>
static struct { unsigned char before; fd_set set; unsigned char after; } data;
static int calls;
static fd_set *get_set(void) { ++calls; return &data.set; }
int main(void) {
    unsigned int i;
    data.before = 17; data.after = 34;
    for (i = 0; i < sizeof(data.set.bytes); ++i) data.set.bytes[i] = 255;
    (FD_ZERO(get_set()), (void)0);
    if (calls != 1 || data.before != 17 || data.after != 34) return 1;
    for (i = 0; i < sizeof(data.set.bytes); ++i) if (data.set.bytes[i]) return 2;
    return 0;
}
""")
command = [a.host_cc, '-std=c89', '-pedantic-errors', '-Wall', '-Wextra', '-Werror',
           '-fno-builtin', '-O2', '-I', str(ROOT / 'nextstepcompat/include'),
           str(source), '-o', str(out / 'standalone')]
result = subprocess.run(command, capture_output=True, text=True)
rows.append(dict(case='standalone ISO C89 compilation', command=command,
                 passed=result.returncode == 0, stderr=result.stderr))
if result.returncode == 0:
    result = subprocess.run([str(out / 'standalone')], capture_output=True, text=True)
    rows.append(dict(case='standalone FD_ZERO execution', passed=result.returncode == 0,
                     stderr=result.stderr))

# Reject a mismatched modern bundle before creating build output or backups.
result = subprocess.run([sys.executable, str(tc / 'libexec/nextstep/prepare-sdk.py'),
                         '--header-policy-version'], capture_output=True, text=True)
rows.append(dict(case='current SDK-helper preflight', passed=result.returncode == 0
                 and result.stdout.strip() == '1', stderr=result.stderr))
old = out / 'old-toolchain'
helper = old / 'libexec/nextstep/prepare-sdk.py'
helper.parent.mkdir(parents=True)
helper.write_text('print("0")\n')
for script in ['build.py', 'install.py']:
    destination = out / ('refused-' + script)
    command = [sys.executable, str(ROOT / 'nextstepcompat' / script), '--toolchain', str(old)]
    if script == 'build.py':
        command += ['--sdk', str(sdk), '--output', str(destination)]
    else:
        command += ['--build', str(out / 'unused-build'), '--backup', str(destination)]
    result = subprocess.run(command, capture_output=True, text=True)
    rows.append(dict(case=script + ' SDK-helper preflight',
                     passed=result.returncode != 0 and not destination.exists()
                     and 'updated toolchain SDK preparer' in result.stderr,
                     stderr=result.stderr))
report = dict(passed=all(row['passed'] for row in rows), cases=rows,
              helper_hashes={f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                             for f in (ROOT / 'nextstepcompat/include').glob('ns33-f*.h')})
(out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
for row in rows:
    if not row['passed']:
        print(row.get('arch', ''), row.get('standard', ''), row['case'], row['stderr'])
print(str(sum(row['passed'] for row in rows)) + '/' + str(len(rows)) + ' passed')
raise SystemExit(0 if report['passed'] else 1)
