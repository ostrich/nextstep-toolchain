#!/usr/bin/env python3
"""Build and inspect a NIHS fixed-VM diamond dependency graph on Linux.

Leaves products for subsequent runtime checks; this test is not runtime proof.
"""
import argparse
import json
import runpy
from pathlib import Path
import struct
import subprocess

ARCHES = ['m68k', 'i386', 'hppa', 'sparc']
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--canonical', action='store_true')
a = p.parse_args()
tc, sdk, root = a.toolchain.resolve(), a.sdk.resolve(), a.output.resolve()
root.mkdir(parents=True, exist_ok=False)
steps = []
def run(*args):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    steps.append({'command': list(map(str, args)), 'exitcode': result.returncode,
                  'stdout': result.stdout, 'stderr': result.stderr})
    (root / 'commands.json').write_text(json.dumps(steps, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout

def commands(path, arch):
    thin = root / (path.name + '.' + arch)
    run(tc / 'libexec/cctools/lipo', path, '-thin', arch, '-output', thin)
    raw = thin.read_bytes()
    endian = '<' if raw[:4] == b'\xce\xfa\xed\xfe' else '>'
    assert struct.unpack_from(endian + 'I', raw)[0] == 0xfeedface
    offset, loads = 28, []
    for _ in range(struct.unpack_from(endian + 'I', raw, 16)[0]):
        cmd, size = struct.unpack_from(endian + 'II', raw, offset)
        if cmd in (6, 7):
            name, version, address = struct.unpack_from(endian + 'III', raw, offset + 8)
            loads.append((cmd, raw[offset + name:offset + size].split(b'\0')[0].decode(), version, address))
        offset += size
    return loads

sources = {
    'leaf': 'int leaf(void){return 7;}\n',
    'left': 'extern int leaf(void); int left(void){return leaf()+11;}\n',
    'right': 'extern int leaf(void); int right(void){return leaf()+13;}\n',
    'top': 'extern int left(void),right(void); int top(void){return left()+right();}\n',
}
deps = {'leaf': [], 'left': ['leaf'], 'right': ['leaf'], 'top': ['left', 'right']}
for index, (name, source) in enumerate(sources.items()):
    (root / (name + '.c')).write_text(source)
    address = 0x29000000 + index * 0x200000
    spec = {'install_name': '/usr/local/lib/libdep' + name + '.1.shlib',
            'minor_version': 1, 'addresses': {'text': hex(address), 'data': hex(address + 0x100000)},
            'segment_reservation': '0x100000', 'exports': ['_' + name, None, None]}
    if a.canonical:spec['canonical_entries']=True
    (root / (name + '.json')).write_text(json.dumps(spec, indent=2) + '\n')
    run(tc / 'bin/nextstep-gcc', '--sdk', sdk, '-O2',
        *(['--shared-exports',root/(name+'.json')] if a.canonical else []),
        *[v for arch in ARCHES for v in ('-arch', arch)], '-c',
        root / (name + '.c'), '-o', root / (name + '.o'))
    # Use an archive root, including an intentionally incompatible convenience
    # copy of leaf. A dependency must satisfy leaf before archive extraction;
    # otherwise the duplicate is embedded or produces a multiple definition.
    members=[root/(name+'.o')]
    if name=='left':
        (root/'duplicate.c').write_text('int leaf(void){return 900;} int duplicate_marker(void){return 901;}\n')
        run(tc/'bin/nextstep-gcc','--sdk',sdk,'-O2',
            *[v for arch in ARCHES for v in ('-arch',arch)],'-c',
            root/'duplicate.c','-o',root/'duplicate.o')
        members.append(root/'duplicate.o')
    archive=root/(name+'-input.a')
    run(tc/'libexec/cctools/libtool','-static','-o',archive,*members)
    run(tc / 'bin/nextstep-shlib', '--sdk', sdk, '--spec', root / (name + '.json'),
        '--output', root / ('libdep' + name + '.1.shlib'), '--import-library', root / (name + '.a'),
        '--build-record', root / (name + '-build.json'),
        *[v for dep in deps[name] for v in ('--dependency', root / (dep + '.a'))],
        archive)
    if name=='left':
        symbols=run(tc/'libexec/cctools/nm','-g',root/('libdep'+name+'.1.shlib'))
        assert '_duplicate_marker' not in symbols, symbols
(root / 'main.c').write_text('#include <stdio.h>\nextern int top(void); int main(void){int v=top(); printf("dependency result %d\\n",v); return v!=38;}\n')
run(tc / 'bin/nextstep-gcc', '--sdk', sdk, '-O2',
    *[v for arch in ARCHES for v in ('-arch', arch)],
    root / 'main.c', root / 'top.a', '-o', root / 'consumer')
expected = {'/usr/local/lib/libdep' + name + '.1.shlib' for name in sources}
results = {}
for arch in ARCHES:
    loads = commands(root / 'consumer', arch)
    project = [entry[1] for entry in loads if entry[1].startswith('/usr/local/')]
    assert set(project) == expected and len(project) == len(expected), (arch, loads)
    for name in sources:
        runtime = commands(root / ('libdep' + name + '.1.shlib'), arch)
        assert len(runtime) == 1 and runtime[0][0] == 7, (arch, name, runtime)
    results[arch] = loads
    print('PASS diamond import closure ' + arch)
# Reject bad graphs before publishing any runtime/import outputs.
def rejected(name, changes, dependencies, diagnostic):
    spec=json.loads((root/'top.json').read_text());spec.update(changes)
    directory=root/name;directory.mkdir()
    (directory/'spec.json').write_text(json.dumps(spec))
    command=[tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',directory/'spec.json',
             '--output',directory/'runtime.shlib','--import-library',directory/'import.a',
             '--build-record',directory/'record.json',
             *[value for dependency in dependencies for value in ('--dependency',dependency)],root/'top.o']
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True)
    assert result.returncode and diagnostic in result.stderr,(name,result.stderr)
    assert not (directory/'runtime.shlib').exists() and not (directory/'import.a').exists()
    print('PASS rejection '+name)
rejected('cycle',{'install_name':'/usr/local/lib/libdepleaf.1.shlib'},[root/'leaf.a'],'Dependency cycle')
rejected('future-reservation-overlap',{'addresses':{'text':'0x29080000','data':'0x29900000'}},
         [root/'left.a',root/'right.a'],'overlaps parent reservation')
rejected('parent-overlap',{'addresses':{'text':'0x29000000','data':'0x29100000'}},
         [root/'left.a',root/'right.a'],'overlaps parent reservation')
# Same runtime name, a different mapping: each input alone is valid, together
# they cannot describe a consistent installed dependency.
alternate=json.loads((root/'leaf.json').read_text())
alternate['addresses']={'text':'0x2a000000','data':'0x2a100000'}
(root/'alternate.json').write_text(json.dumps(alternate))
run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',root/'alternate.json',
    '--output',root/'alternate.shlib','--import-library',root/'alternate.a',
    '--build-record',root/'alternate-build.json',root/'leaf.o')
rejected('identity-conflict',{},[root/'leaf.a',root/'alternate.a'],'Conflicting dependency identity')
# The closure must retain full reservations, including empty data segments.
read_imports=runpy.run_path(str(tc/'bin/nextstep-shlib'))['import_identities']
for arch in ARCHES:
    thin=root/('top-import.'+arch+'.a')
    run(tc/'libexec/cctools/lipo',root/'top.a','-thin',arch,'-output',thin)
    identities=read_imports(thin)
    assert len(identities)==4,(arch,identities)
    assert all(len(item['segments'])==2 and all(size==0x100000 for _,size in item['segments'])
               for item in identities.values()),(arch,identities)
    print('PASS complete closure reservations '+arch)
# An absent architecture must fail before outputs are published.
run(tc/'libexec/cctools/lipo',root/'leaf.a','-extract','i386','-output',root/'leaf-i386.a')
rejected('missing-slice',{},[root/'leaf-i386.a'],'m68k')
malformed=root/'malformed.a'
raw=bytearray((root/'top-import.i386.a').read_bytes())
raw[8+48:8+58]=b'-1        '
malformed.write_bytes(raw)
try:
    read_imports(malformed)
except ValueError as error:
    assert 'Negative import archive member size' in str(error)
else:
    raise AssertionError('Negative archive member size accepted')
print('PASS malformed dependency archive rejection')
# A compatible leaf update keeps branch slots and addresses unchanged.
upgrade=json.loads((root/'leaf.json').read_text());upgrade['minor_version']=2
(root/'upgrade.json').write_text(json.dumps(upgrade))
(root/'upgrade.c').write_text('int leaf(void){return 8;}\n')
run(tc/'bin/nextstep-gcc','--sdk',sdk,'-O2',
    *(['--shared-exports',root/'upgrade.json'] if a.canonical else []),
    *[v for arch in ARCHES for v in ('-arch',arch)],'-c',root/'upgrade.c','-o',root/'upgrade.o')
run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',root/'upgrade.json',
    '--output',root/'leaf-upgrade.shlib','--import-library',root/'upgrade.a',
    '--build-record',root/'upgrade-build.json',root/'upgrade.o')
(root/'require2.c').write_text('#include <stdio.h>\nextern int leaf(void); int main(void){int v=leaf();printf("leaf result %d\\n",v);return v!=8;}\n')
run(tc/'bin/nextstep-gcc','--sdk',sdk,'-O2',
    *[v for arch in ARCHES for v in ('-arch',arch)],root/'require2.c',root/'upgrade.a','-o',root/'require2')
for arch in ARCHES:
    loads=commands(root/'require2',arch)
    assert any(item[1]=='/usr/local/lib/libdepleaf.1.shlib' and item[2]==2 for item in loads)
# Old transitive consumers and a newer direct import are compatible. The
# version floor must not depend on which duplicate load member appears first.
(root/'mixed-main.c').write_text('#include <stdio.h>\nextern int top(void); int main(void){int v=top();printf("mixed dependency result %d\\n",v);return v!=40;}\n')
for index,dependencies in enumerate([[root/'left.a',root/'right.a',root/'upgrade.a'],
                                    [root/'upgrade.a',root/'right.a',root/'left.a']]):
    directory=root/('mixed-'+str(index));directory.mkdir()
    run(tc/'bin/nextstep-shlib','--sdk',sdk,'--spec',root/'top.json',
        '--output',directory/'runtime.shlib','--import-library',directory/'import.a',
        '--build-record',directory/'build.json',
        *[value for dependency in dependencies for value in ('--dependency',dependency)],
        root/'top-input.a')
    run(tc/'bin/nextstep-gcc','--sdk',sdk,'-O2',
        *[v for arch in ARCHES for v in ('-arch',arch)],root/'mixed-main.c',
        directory/'import.a','-o',root/('mixed-consumer-'+str(index)))
    for arch in ARCHES:
        loads=commands(root/('mixed-consumer-'+str(index)),arch)
        leaf=[item for item in loads if item[1]=='/usr/local/lib/libdepleaf.1.shlib']
        assert len(leaf)==1 and leaf[0][2]==2,(index,arch,loads)
    print('PASS mixed minor version closure order '+str(index))
(root/'run-dependencies.sh').write_text('''#!/bin/sh
cd "$1" || exit 90
leaf=/usr/local/lib/libdepleaf.1.shlib
./consumer > baseline.log 2>&1
status=$?
cat baseline.log
test "$status" = 0 || exit 1
mv "$leaf" "$leaf.hidden" || exit 2
./consumer > missing.log 2>&1
status=$?
mv "$leaf.hidden" "$leaf" || exit 3
test "$status" != 0 || exit 4
echo 'PASS missing transitive runtime'
./require2 > insufficient.log 2>&1
status=$?
test "$status" != 0 || exit 5
echo 'PASS insufficient minor version'
for program in mixed-consumer-0 mixed-consumer-1; do
 ./$program > "$program.insufficient.log" 2>&1
 status=$?
 test "$status" != 0 || exit 13
done
echo 'PASS mixed closure enforces highest minor version'
cp "$leaf" leaf-original.shlib || exit 6
cp leaf-upgrade.shlib "$leaf" || exit 7
chmod 755 "$leaf"
./consumer > upgrade.log 2>&1
status=$?
cat upgrade.log
grep 'dependency result 40' upgrade.log >/dev/null || exit 8
test "$status" = 1 || exit 9
./require2 || exit 10
./mixed-consumer-0 || exit 14
./mixed-consumer-1 || exit 15
echo 'PASS compatible upgrade with unchanged consumer'
cp leaf-original.shlib "$leaf" || exit 11
chmod 755 "$leaf"
./consumer || exit 12
echo 'PASS dependency batch complete'
''')
(root/'run-dependencies.sh').chmod(0o755)
(root / 'host-validation.json').write_text(json.dumps({'status': 'passed', 'runtime_tested': False,
                                                       'load_commands': results}, indent=2) + '\n')
