#!/usr/bin/env python3
"""Build native/compat API probes and pinned libc-test programs; never boot a VM."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from selections import prepare, sources as test_sources

HERE = Path(__file__).resolve().parent
ARCHES = ('i386', 'm68k', 'sparc', 'hppa')
TESTS = ('string', 'string_iso', 'memory_boundaries', 'stdio_boundaries', 'portable_apis', 'environment_time', 'time_calendar', 'string_strcspn', 'string_strstr', 'strtol',
         'strtod_simple', 'snprintf', 'sscanf', 'ungetc', 'strftime', 'qsort')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolchain', type=Path, required=True)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--compat-build', type=Path, help='New component build to test before staging a compiler')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--arch', choices=ARCHES, action='append')
    p.add_argument('--allow-stale-toolchain', action='store_true', help='Explicitly permit an older compiler patch snapshot for comparisons')
    a = p.parse_args()
    tc, sdk, out = (x.resolve() for x in (a.toolchain, a.sdk, a.output))
    if out.exists():
        p.error('Use a new output directory')
    if a.jobs < 1 or a.jobs > 32:
        p.error('--jobs must be 1..32')
    driver = tc / 'bin/nextstep-gcc'
    if not driver.is_file() or not (sdk / 'lib/libsys_s.a').is_file():
        p.error('An installed toolchain and NEXTSTEP SDK are required')
    manifest = json.loads((tc / 'toolchain.json').read_text())
    patches = HERE.parents[2] / 'patches'
    current_patches = {line: digest(patches / line) for line in (patches / 'series').read_text().splitlines()
                       if line and not line.startswith('#')}
    if not a.allow_stale_toolchain and manifest['gcc_patches_sha256'] != current_patches:
        p.error('Compiler snapshot lacks current patches; use the current bundle or explicitly --allow-stale-toolchain')
    compat_build = a.compat_build.resolve() if a.compat_build else None
    if compat_build and not (compat_build / 'build-record.json').is_file():
        p.error('Missing compatibility build record')
    pin = json.loads((HERE / 'upstream.lock.json').read_text())
    for name, expected in pin['files'].items():
        if digest(HERE / 'upstream' / name) != expected:
            p.error('Pristine upstream file changed: ' + name)
    out.mkdir(parents=True)
    prepare(HERE, out / 'selected')
    empty = out / 'native-headers'
    empty.mkdir()
    # This is infrastructure for upstream's PRIu64 diagnostics, not an API
    # implementation or evidence that the native SDK supplies inttypes.h.
    adapter = out / 'test-headers'
    adapter.mkdir()
    (adapter / 'inttypes.h').write_text('#include <stdint.h>\n#define PRIu64 "llu"\n')
    interfaces = json.loads((HERE / 'apis.json').read_text())['interfaces']

    def command(arch, mode):
        cmd = [sys.executable, str(driver), '--sdk', str(sdk), '-arch', arch,
               '-O2', '-std=gnu99', '-fno-builtin']
        if mode == 'native':
            cmd += ['--compat-headers', str(empty), '-nodefaultlibs']
        elif compat_build:
            cmd += ['--compat-headers', str(HERE.parents[1] / 'include'), '-nodefaultlibs']
        return cmd

    def libraries(arch, mode):
        native = [str(tc / 'lib' / arch / 'libgcc.a'), str(sdk / 'lib/libsys_s.a')]
        if mode == 'compat' and compat_build:
            return [str(compat_build / arch / 'libnextstepcompat.a'), *native]
        return native if mode == 'native' else []

    def run(cmd, log):
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=90)
            log.write_bytes(r.stdout)
            return r.returncode
        except subprocess.TimeoutExpired as e:
            log.write_bytes((e.stdout or b'') + b'\nAUDIT TOOL TIMEOUT\n')
            return 124

    def build(arch, mode):
        d = out / arch / mode
        d.mkdir(parents=True)
        entries = []
        macros = {}
        for header in sorted({api['header'] for api in interfaces}):
            src = d / ('header-' + header.replace('/', '-') + '.c')
            src.write_text('#include <' + header + '>\n')
            r = subprocess.run(command(arch, mode) + ['-E', '-dM', str(src)],
                               capture_output=True, timeout=90)
            (d / (src.stem + '.log')).write_bytes(r.stderr)
            macros[header] = {line.split()[1].split(b'(')[0].decode()
                              for line in r.stdout.splitlines() if line.startswith(b'#define ')}
        for api in interfaces:
            n = api['name']
            src, obj = d / (n + '.c'), d / (n + '.o')
            body = ('void (*volatile audit_symbol)(void) = (void (*)(void))' + n + ';\n'
                    'int main(void) { return audit_symbol == 0; }\n')
            src.write_text('#include <' + api['header'] + '>\n' + body)
            declared = run(command(arch, mode) + ['-Werror=implicit-function-declaration',
                           '-c', str(src), '-o', str(obj)], d / (n + '-declaration.log')) == 0
            if declared:
                link_input = obj
            else:
                link_input = d / (n + '-symbol.c')
                link_input.write_text('extern void ' + n + '(void);\n' + body)
            linked = run(command(arch, mode) + [str(link_input), *libraries(arch, mode),
                         '-o', str(d / (n + '-link'))], d / (n + '-link.log')) == 0
            entries.append({**api, 'macro': n in macros[api['header']], 'declaration': 'present' if declared else 'failed',
                            'link': 'present' if linked else 'failed',
                            'behavior': 'untested'})
        tests = {}
        for name in TESTS:
            sources = test_sources(HERE, out, name)
            dest = out / arch / (mode + '-' + name)
            cmd = command(arch, mode) + ['-I', str(HERE / 'upstream/src/common')]
            if name == 'qsort' and mode == 'native':
                cmd += ['-I', str(adapter)]
            if mode == 'compat':
                cmd += ['-DNS33_COMPAT']
            if name == 'snprintf':
                # Test fixture constant; the original SDK does not expose M_PI.
                cmd += ['-DM_PI=3.14159265358979323846']
            cmd += list(map(str, sources)) + libraries(arch, mode) + ['-o', str(dest)]
            code = run(cmd, d / (name + '-test-build.log'))
            tests[name] = {'build': 'passed' if code == 0 else 'failed',
                           'run': 'untested', 'command': cmd}
        print(arch, mode, 'availability probes and upstream builds complete', flush=True)
        return arch, mode, {'interfaces': entries, 'tests': tests}

    results = {arch: {} for arch in a.arch or ARCHES}
    tasks = [(arch, mode) for arch in results for mode in ('native', 'compat')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for arch, mode, result in pool.map(lambda args: build(*args), tasks):
            results[arch][mode] = result
    record = {'schema': 1, 'upstream_commit': pin['commit'],
              'toolchain_manifest_sha256': digest(tc / 'toolchain.json'),
              'sdk_library_sha256': digest(sdk / 'lib/libsys_s.a'),
              'inventory_sha256': digest(HERE / 'apis.json'),
              'audit_sha256': digest(Path(__file__)),
              'driver_sha256': digest(driver),
              'harness_sha256': digest(HERE / 'harness.c'),
              'selected_sources_sha256': {p.name: digest(p) for p in sorted((out / 'selected').iterdir()) if p.is_file()},
              'note': 'Availability is not behavior or signature conformance. Native mode retains SDK syntax repairs and GCC runtime only.',
              'results': results}
    if compat_build:
        record['compatibility_build'] = {
            'record_sha256': digest(compat_build / 'build-record.json'),
            'libraries_sha256': {arch: digest(compat_build / arch / 'libnextstepcompat.a') for arch in results}}
    (out / 'build-results.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Recorded:', out / 'build-results.json')


if __name__ == '__main__':
    main()
