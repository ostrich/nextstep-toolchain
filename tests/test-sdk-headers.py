#!/usr/bin/env python3
"""Check SDK header independence, modern syntax and original POSIX layouts."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--output', type=Path, default=ROOT / 'work/sdk-header-tests')
p.add_argument('--jobs', type=int, default=4)
a = p.parse_args()
sdk, tc, out = [x.resolve() for x in (a.sdk, a.toolchain, a.output)]
out.mkdir(parents=True, exist_ok=True)
overlay = out / 'overlay'
preparer = tc / 'libexec/nextstep/prepare-sdk.py'
if preparer.read_bytes() != (ROOT / 'tools/prepare-sdk.py').read_bytes():
    raise SystemExit('Stage the current SDK preparer before testing the bundle.')
subprocess.run(['python3', str(preparer), '--sdk', str(sdk),
                '--output', str(overlay)], check=True)
headers = ['sys/types.h', 'bsd/sys/types.h', 'fcntl.h', 'sys/fcntl.h',
           'bsd/sys/fcntl.h', 'signal.h', 'ansi/signal.h', 'sys/signal.h',
           'bsd/sys/signal.h', 'sys/stat.h', 'unistd.h', 'sys/socket.h',
           'sys/time.h', 'sys/resource.h', 'stdio.h', 'stdlib.h', 'string.h',
           'strings.h', 'time.h', 'math.h', 'limits.h', 'dirent.h', 'sys/ioctl.h',
           'errno.h', 'sys/wait.h', 'sys/param.h', 'sys/uio.h', 'netinet/in.h',
           'arpa/inet.h', 'netdb.h', 'utime.h', 'sys/file.h', 'pwd.h', 'grp.h',
           'termios.h', 'nextstepcompat.h', 'ns33-multibyte.h', 'wchar.h', 'wctype.h']
for header in headers:
    (out / (header.replace('/', '-') + '.c')).write_text(
        '#include <' + header + '>\n#include <' + header + '>\nint probe;\n')

api = out / 'api.c'
api.write_text('''#include <fcntl.h>
#include <signal.h>
#include <sys/stat.h>
#include <unistd.h>
#include <wchar.h>
#include <wctype.h>
#define CHECK(name, type) _Static_assert(__builtin_types_compatible_p(__typeof__(&(name)), type), #name)
CHECK(open, int (*)(const char *, int, ...));
CHECK(creat, int (*)(const char *, mode_t));
CHECK(fcntl, int (*)(int, int, ...));
CHECK(sigprocmask, int (*)(int, const sigset_t *, sigset_t *));
CHECK(sigaction, int (*)(int, const struct sigaction *, struct sigaction *));
CHECK(sigpending, int (*)(sigset_t *));
CHECK(sigsuspend, int (*)(const sigset_t *));
CHECK(sigemptyset, int (*)(sigset_t *));
CHECK(sigfillset, int (*)(sigset_t *));
CHECK(sigaddset, int (*)(sigset_t *, int));
CHECK(sigdelset, int (*)(sigset_t *, int));
CHECK(sigismember, int (*)(const sigset_t *, int));
CHECK(mkfifo, int (*)(const char *, mode_t));
_Static_assert(SA_RESTART != SA_ONSTACK, "distinct signal options");
CHECK(stat, int (*)(const char *, struct stat *));
CHECK(read, ssize_t (*)(int, void *, size_t));
CHECK(write, ssize_t (*)(int, const void *, size_t));
CHECK(mbrtowc, size_t (*)(wchar_t *, const char *, size_t, mbstate_t *));
CHECK(wcrtomb, size_t (*)(char *, wchar_t, mbstate_t *));
CHECK(iswctype, int (*)(wint_t, wctype_t));
_Static_assert(sizeof(wchar_t) == 2 && sizeof(wint_t) == 4, "wide ABI");
_Static_assert(sizeof(mbstate_t) == 16, "conversion state ABI");
void handler(int number) { (void)number; }
void install(void) { signal(SIGUSR1, handler); }
''')
callback = out / 'callback.c'
callback.write_text('''#include <signal.h>
void handler(int number) { (void)number; }
void install(void) {
    struct sigaction action;
    void (*default_handler)(int) = SIG_DFL;
    void (*ignored_handler)(int) = SIG_IGN;
    action.sa_handler = handler;
    signal(SIGUSR1, action.sa_handler);
    action.sa_handler = default_handler;
    signal(SIGUSR1, ignored_handler);
}
''')
abi = out / 'abi.c'
abi.write_text('''#include <sys/types.h>
#include <stddef.h>
#include <sys/stat.h>
#include <sys/fcntl.h>
#include <sys/signal.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <netinet/in.h>
#include <netdb.h>
#define SIZE(t) sizeof(t), __alignof__(t)
#define OFF(t, f) __builtin_offsetof(t, f)
unsigned long sdk_layouts[] = {
 SIZE(dev_t), SIZE(ino_t), SIZE(mode_t), SIZE(nlink_t), SIZE(uid_t), SIZE(gid_t),
 SIZE(off_t), SIZE(pid_t), SIZE(ssize_t), SIZE(size_t), SIZE(sigset_t),
 SIZE(struct stat), OFF(struct stat, st_dev), OFF(struct stat, st_ino),
 OFF(struct stat, st_mode), OFF(struct stat, st_nlink), OFF(struct stat, st_uid),
 OFF(struct stat, st_gid), OFF(struct stat, st_size), OFF(struct stat, st_atime),
 SIZE(struct flock), OFF(struct flock, l_start), OFF(struct flock, l_len),
 OFF(struct flock, l_pid), SIZE(struct sigaction), OFF(struct sigaction, sa_mask),
 OFF(struct sigaction, sa_flags), SIZE(struct sockaddr), SIZE(struct timeval),
 SIZE(struct rusage), SIZE(fd_set), O_RDONLY, O_CREAT, F_GETFD, SIG_BLOCK,
 SIG_SETMASK, SIGUSR1, SIZE(struct in_addr), SIZE(struct sockaddr_in),
 OFF(struct sockaddr_in, sin_addr), SIZE(struct hostent),
 OFF(struct hostent, h_addr_list), SIZE(struct netent), SIZE(struct servent)
};
''')

def command(arch, standard, source, modern=True):
    gcc = tc / 'libexec/gcc' / arch
    cmd = [str(gcc / 'xgcc'), '-B' + str(gcc) + '/', '-D_NEXT_SOURCE',
           '-nostdinc', '-O2', '-std=' + standard]
    if modern:
        configuration = json.loads((tc / 'toolchain.json').read_text())
        cmd += ['-isystem', str(tc / configuration['cxx_runtime'][arch]['compat_headers']),
                '-isystem', str(overlay)]
    else:
        cmd += ['-D_POSIX_SOURCE=1', '-Wno-implicit-int']
    cmd += ['-isystem', str(gcc / 'include'), '-idirafter', str(sdk / 'usr/include'),
            '-idirafter', str(sdk / 'usr/include/ansi'),
            '-idirafter', str(sdk / 'usr/include/bsd')]
    if standard.startswith('c++'):
        cmd += ['-x', 'c++']
    else:
        cmd += ['-Werror=implicit-function-declaration',
                '-Werror=incompatible-pointer-types']
        if modern:
            cmd += ['-Werror=implicit-int']
    return cmd + ['-fsyntax-only', str(source)]

def run(case):
    arch, standard, header = case
    source = (api if header == 'api' else callback if header == 'callback'
              else out / (header.replace('/', '-') + '.c'))
    cmd = command(arch, standard, source)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {'arch': arch, 'standard': standard, 'case': header, 'command': cmd,
            'exitcode': r.returncode, 'stderr': r.stderr, 'passed': r.returncode == 0}

arches = ['i386', 'm68k', 'sparc', 'hppa']
cases = [(arch, std, h) for arch in arches
         for std in ['gnu89', 'gnu17', 'gnu23', 'c++17'] for h in headers]
cases += [(arch, 'gnu17', 'api') for arch in arches]
cases += [(arch, std, 'callback') for arch in arches
          for std in ['gnu89', 'gnu17', 'gnu23', 'c++17']]
with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
    records = list(pool.map(run, cases))

for arch in arches:
    entry = {'arch': arch, 'case': 'original POSIX ABI comparison', 'steps': []}
    for modern in [False, True]:
        assembly = out / (arch + ('-modern.s' if modern else '-original.s'))
        cmd = command(arch, 'gnu89', abi, modern)
        cmd[cmd.index('-fsyntax-only')] = '-S'
        cmd += ['-o', str(assembly)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        entry['steps'].append({'command': cmd, 'exitcode': r.returncode, 'stderr': r.stderr})
    entry['passed'] = (all(s['exitcode'] == 0 for s in entry['steps']) and
                       (out / (arch + '-modern.s')).read_bytes() ==
                       (out / (arch + '-original.s')).read_bytes())
    records.append(entry)
report = {'cases': records, 'passed': all(r['passed'] for r in records),
          'preparer_sha256': hashlib.sha256(preparer.read_bytes()).hexdigest()}
(out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
for row in records:
    if not row['passed']:
        print(row['arch'], row.get('standard', ''), row['case'], 'FAIL')
        print(row.get('stderr', row.get('steps')))
print(str(sum(r['passed'] for r in records)) + '/' + str(len(records)) + ' passed')
raise SystemExit(0 if report['passed'] else 1)
