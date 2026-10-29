#!/usr/bin/env python3
"""Stage a relocatable Linux-hosted compiler, without proprietary SDK files."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from build_inputs import digest, patch_hashes
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--build-set', type=Path, help='Explicit coherent C++ compiler/runtime build set')
p.add_argument('--keep-host-debug', action='store_true', help='Keep host executable debug data in a C++ bundle')
a = p.parse_args()
prefix = a.prefix.resolve()
if prefix.exists():
    p.error('Use a new prefix; existing installations are never overwritten')
arches = ['i386', 'm68k', 'sparc', 'hppa']
configuration = json.loads(a.build_set.read_text()) if a.build_set else None
if configuration and set(configuration['targets']) != set(arches):
    p.error('Build set must describe all four targets')
def selected(arch, field, default):
    return (ROOT / configuration['targets'][arch][field]).resolve() if configuration else ROOT / default
host = (ROOT / configuration['host_tools']).resolve() if configuration else ROOT / 'work/host-tools'
current_patches = patch_hashes(ROOT)
strip_host = bool(configuration) and not a.keep_host_debug
if strip_host and shutil.which('strip') is None:
    p.error('Host strip is required, or use --keep-host-debug')
# Reject stale or failed build products before creating the installation.
for arch in arches:
    build = selected(arch, 'compiler', 'work/build-' + arch)
    compiler_record = json.loads((build / 'build-record.json').read_text())
    for name in ['xgcc', 'cc1', 'cc1plus', 'cc1obj', 'cc1objplus']:
        if compiler_record.get('compiler_sha256', {}).get(name) != digest(build / 'gcc' / name):
            p.error('Compiler provenance mismatch: ' + arch + '/' + name)
    runtime_dir = selected(arch, 'basic_runtime', 'work/runtime-host-' + arch)
    runtime_record = json.loads((runtime_dir / 'build-record.json').read_text())
    if (not all(row['passed'] for row in runtime_record['helpers']) or
        runtime_record.get('archive_sha256') != digest(runtime_dir / 'libgcc.a')):
        p.error('Failed or stale runtime archive: ' + arch)
    if configuration:
        if compiler_record['patches_sha256'] != current_patches or compiler_record['thread_model'] != 'nextstep':
            p.error('Compiler does not match the current native-threaded snapshot: ' + arch)
        if runtime_record['compiler_sha256'] != digest(build / 'gcc/cc1'):
            p.error('Basic runtime uses another compiler snapshot: ' + arch)
        cxx = selected(arch, 'cxx_runtime', '')
        atomic = selected(arch, 'atomic_runtime', '')
        cr = json.loads((cxx / 'build-record.json').read_text())
        ar = json.loads((atomic / 'build-record.json').read_text())
        for record, label in [(cr, 'C++'), (ar, 'atomic')]:
            if (record['arch'] != arch or record['patches_sha256'] != current_patches or
                any(step['exitcode'] != 0 for step in record['steps'])):
                p.error('Failed or stale ' + label + ' runtime: ' + arch)
            for name, expected in record['compiler_sha256'].items():
                if digest(build / 'gcc' / name) != expected:
                    p.error(label + ' runtime uses another compiler: ' + arch)
        if cr['phase'] != 'all' or cr['thread_model'] != 'nextstep':
            p.error('Incomplete C++ runtime: ' + arch)
        code_suffixes = ('.c', '.h', '.patch', '.json')
        current_compatibility = {str(n.relative_to(ROOT)): digest(n)
            for n in (ROOT / 'runtime').rglob('*') if n.is_file() and n.suffix in code_suffixes}
        built_compatibility = {n: h for n, h in cr['compatibility_sha256'].items()
                               if Path(n).suffix in code_suffixes}
        if built_compatibility != current_compatibility:
            p.error('Compatibility sources changed after build: ' + arch)
        current_libc_compatibility = {str(n.relative_to(ROOT / 'nextstepcompat')): digest(n)
            for n in sorted((ROOT / 'nextstepcompat').rglob('*'))
            if n.is_file() and '__pycache__' not in n.parts
            and n.relative_to(ROOT / 'nextstepcompat').parts[0] != 'tests'}
        def library_inputs(hashes):
            # Test fixtures are not inputs to the library build. Their own
            # validation records identify the exact tested executables.
            return {n: h for n, h in hashes.items() if not n.startswith('tests/')}
        if library_inputs(cr.get('nextstepcompat_sha256', {})) != current_libc_compatibility:
            p.error('NextStepCompat sources changed after build: ' + arch)
        nr = json.loads((cxx / 'nextstepcompat/build-record.json').read_text())
        if (nr.get('status') != 'passed' or
            library_inputs(nr['sources_sha256']) != current_libc_compatibility or
            nr['targets'][arch]['archive_sha256'] !=
                digest(cxx / 'nextstepcompat' / arch / 'libnextstepcompat.a')):
            p.error('Failed or stale NextStepCompat build: ' + arch)
        current_atomic_headers = {str(n.relative_to(ROOT)): digest(n)
            for n in (ROOT / 'nextstepcompat/include').rglob('*') if n.is_file()}
        if ar['compatibility_headers_sha256'] != current_atomic_headers:
            p.error('Compatibility headers changed after atomic build: ' + arch)
        artifacts = {'libstdc++.a': cxx / 'src/.libs/libstdc++.a',
                     'libsupc++.a': cxx / 'libsupc++/.libs/libsupc++.a',
                     'libgcc_eh.a': cxx / 'libgcc_eh.a',
                     'libnextstepcompat.a': cxx / 'nextstepcompat' / arch / 'libnextstepcompat.a',
                     'libnextstep-cxx-compat.a': cxx / 'libnextstep-cxx-compat.a',
                     'crt-nextstep.o': cxx / 'crt-nextstep.o'}
        for name, path in artifacts.items():
            if cr['artifacts'][name] != digest(path):
                p.error('C++ runtime artifact mismatch: ' + arch + '/' + name)
        if ar['artifact_sha256'] != digest(atomic / '.libs/libatomic.a'):
            p.error('Atomic archive artifact mismatch: ' + arch)
        for path in [*artifacts.values(), atomic / '.libs/libatomic.a']:
            if path.suffix == '.a':
                members = subprocess.check_output([str(host / 'bin/ar'), 't', str(path)], text=True).splitlines()
                if any(name.endswith('.a') for name in members):
                    p.error('Nested archive in runtime: ' + str(path))
host_record = json.loads((host / 'build-record.json').read_text())
if host_record['status'] != 'passed':
    p.error('Host-tools build did not pass')
for name, expected in host_record['binaries_sha256'].items():
    if digest(host / 'bin' / name) != expected:
        p.error('Host tool provenance mismatch: ' + name)
# Preflight before creating an incomplete installation.
items = [(ROOT / 'tools/nextstep-gcc', Path('bin/nextstep-gcc')),
         (ROOT / 'tools/prepare-sdk.py', Path('libexec/nextstep/prepare-sdk.py')),
         (ROOT / 'tools/nextstep-debug.py', Path('libexec/nextstep/nextstep-debug.py'))]
for arch in arches:
    build = selected(arch, 'compiler', 'work/build-' + arch) / 'gcc'
    for name in ['xgcc', 'cc1', 'cc1plus', 'cc1obj', 'cc1objplus']:
        items.append((build / name, Path('libexec/gcc') / arch / name))
    items.append((selected(arch, 'basic_runtime', 'work/runtime-host-' + arch) / 'libgcc.a', Path('lib') / arch / 'libgcc.a'))
    if configuration:
        cxx = selected(arch, 'cxx_runtime', '')
        atomic = selected(arch, 'atomic_runtime', '')
        for name, source in [('libstdc++.a', cxx / 'src/.libs/libstdc++.a'),
                             ('libsupc++.a', cxx / 'libsupc++/.libs/libsupc++.a'),
                             ('libatomic.a', atomic / '.libs/libatomic.a')]:
            items.append((source, Path('lib') / arch / name))
        for name in ['libgcc_eh.a', 'libnextstep-cxx-compat.a', 'crt-nextstep.o']:
            items.append((cxx / name, Path('lib') / arch / name))
        items.append((cxx / 'nextstepcompat' / arch / 'libnextstepcompat.a',
                      Path('lib') / arch / 'libnextstepcompat.a'))
for name in ['as-i386', 'as-m68k', 'as-sparc', 'as-hppa', 'ld', 'lipo', 'libtool', 'nm', 'ar', 'strip']:
    items.append((host / 'bin' / name, Path('libexec/cctools') / name))
for name in ['COPYING3', 'COPYING.RUNTIME']:
    items.append((ROOT / 'work/gcc-16.2.0' / name, Path('share/licenses/gcc') / name))
items.append((host / 'source/APPLE_LICENSE', Path('share/licenses/cctools/APPLE_LICENSE')))
if configuration:
    items.append((ROOT / 'nextstepcompat/format/COPYRIGHT', Path('share/licenses/musl/COPYRIGHT')))
    for name in ['COPYRIGHT', 'TRE-LICENSE.txt']:
        items.append((ROOT / 'nextstepcompat/regex' / name, Path('share/licenses/musl-1.2.6') / name))
    items.append((ROOT / 'nextstepcompat/LICENSE', Path('share/licenses/nextstepcompat/LICENSE')))
    items.append((ROOT / 'toolchain/README.binary.txt', Path('README.txt')))
for source, _ in items:
    if not source.is_file(): p.error('Missing build input: ' + str(source))
record = {'gcc_version': json.loads((ROOT / 'sources.lock.json').read_text())['gcc']['version'],
          'targets': ['i386', 'm68k', 'sparc', 'hppa'], 'gcc_patches_sha256': patch_hashes(ROOT),
          'host_tools': host_record['sources'],
          'host_tools_patch_sha256': host_record['patch_sha256'],
          'host_tools_patches_sha256': host_record.get('patches_sha256', {}),
          'host_compatibility_sha256': host_record['compatibility_sha256'],
          'host_binaries_stripped': strip_host,
          'files': {}}
for source, destination in items:
    destination = prefix / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if strip_host and destination.parts[len(prefix.parts)] == 'libexec':
        with destination.open('rb') as stream:
            is_elf = stream.read(4) == b'\x7fELF'
        if is_elf:
            subprocess.run(['strip', '--strip-unneeded', str(destination)], check=True)
    record['files'][str(destination.relative_to(prefix))] = digest(destination)
for arch in record['targets']:
    shutil.copytree(selected(arch, 'compiler', 'work/build-' + arch) / 'gcc/include', prefix / 'libexec/gcc' / arch / 'include')
    if configuration:
        cxx = selected(arch, 'cxx_runtime', '')
        header_dir = '/include/c++/' + arch
        # Generated libstdc++ install recipes do not quote DESTDIR. Use a
        # whitespace-free temporary stage, then copy to the requested prefix.
        with tempfile.TemporaryDirectory(prefix='nextstep-headers-', dir=ROOT/'work') as header_stage:
            for subdir, targets in [('include', ['install-headers']),
                                    ('libsupc++', ['install-stdHEADERS', 'install-bitsHEADERS'])]:
                subprocess.run(['make', '-s', '-C', str(cxx / subdir),
                                'DESTDIR=' + header_stage, 'gxx_include_dir=' + header_dir, *targets], check=True)
            shutil.copytree(Path(header_stage)/'include', prefix/'include', dirs_exist_ok=True)
        record.setdefault('cxx_runtime', {})[arch] = {
            'headers': ['include/c++/' + arch, 'include/c++/' + arch + '/' + arch + '-next-nextstep3.3'],
            'compat_headers': 'include/nextstepcompat', 'libraries': 'lib/' + arch}
if configuration:
    shutil.copytree(ROOT / 'nextstepcompat/include', prefix / 'include/nextstepcompat')
    # Unwinding is a compiler interface, not part of the libc compatibility API.
    for arch in arches:
        shutil.copyfile(selected(arch, 'cxx_runtime', '') / 'runtime-include/unwind.h',
                        prefix / 'libexec/gcc' / arch / 'include/unwind.h')
    record['nextstepcompat'] = {
        'version': (ROOT / 'nextstepcompat/VERSION').read_text().strip(),
        'headers': 'include/nextstepcompat',
        'sources_sha256': current_libc_compatibility,
        'libraries': {arch: 'lib/' + arch + '/libnextstepcompat.a' for arch in arches}}
    (prefix / 'bin/nextstep-g++').symlink_to('nextstep-gcc')
    # Include copied compiler and public C++ headers in the integrity manifest.
    for name in sorted(prefix.rglob('*')):
        if name.is_file() and not name.is_symlink():
            record['files'][str(name.relative_to(prefix))] = digest(name)
(prefix / 'libexec/cctools/ranlib').symlink_to('libtool')
record['symlinks'] = {'libexec/cctools/ranlib': 'libtool'}
if configuration:
    record['symlinks']['bin/nextstep-g++'] = 'nextstep-gcc'
(prefix / 'toolchain.json').write_text(json.dumps(record, indent=2) + '\n')
if configuration and configuration.get('shared_tools'):
    from shared_support import install
    install(prefix, ROOT / configuration['shared_tools'])
print('Staged compiler in ' + str(prefix))
print('Provide an external NEXTSTEP 3.3 SDK with --sdk or NEXTSTEP_SDK.')
