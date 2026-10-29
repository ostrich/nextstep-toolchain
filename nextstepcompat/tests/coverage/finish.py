#!/usr/bin/env python3
"""Build bounded guest batches, run host controls and render the coverage ledger."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from selections import sources as test_sources

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True, help='Existing audit.py output')
    p.add_argument('--toolchain', type=Path, required=True)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--guest-log', action='append', default=[], metavar='ARCH=FILE')
    a = p.parse_args()
    out, tc, sdk = (x.resolve() for x in (a.output, a.toolchain, a.sdk))
    record = json.loads((out / 'build-results.json').read_text())
    if hashlib.sha256((tc / 'toolchain.json').read_bytes()).hexdigest() != record['toolchain_manifest_sha256']:
        p.error('Toolchain differs from the audited build')
    for name, expected in record.get('selected_sources_sha256', {}).items():
        if hashlib.sha256((out / 'selected' / name).read_bytes()).hexdigest() != expected:
            p.error('Selected test snapshot changed: ' + name)
    host = out / 'host'
    host.mkdir(exist_ok=True)
    host_results = {}
    tests = {}
    for data in next(iter(record['results'].values())).values():
        tests.update(data['tests'])
    for name in tests:
        if tests[name].get('kind') == 'guest-regression':
            host_results[name] = {'scope': 'guest-only'}
            continue
        sources = test_sources(HERE, out, name)
        cmd = ['cc', '-O2', '-fno-builtin', '-DNS33_COMPAT', '-I', str(HERE / 'upstream/src/common'),
               *map(str, sources), '-lm', '-o', str(host / name)]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        (host / (name + '-build.log')).write_bytes(r.stdout + r.stderr)
        status = {'build': r.returncode}
        if r.returncode == 0:
            try:
                r = subprocess.run([str(host / name)], capture_output=True, timeout=20,
                                   env={**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC0'})
                (host / (name + '.log')).write_bytes(r.stdout + r.stderr)
                status['exit'] = r.returncode
            except subprocess.TimeoutExpired:
                status['exit'] = 'timeout'
        host_results[name] = status
    record['host_controls'] = host_results
    for arch, modes in record['results'].items():
        names = [mode + '-' + name for mode, data in modes.items()
                 for name, result in data['tests'].items() if result['build'] == 'passed']
        header = out / arch / 'batch-names.h'
        arguments = []
        for key in names:
            mode, name = key.split('-', 1)
            values = modes[mode]['tests'][name].get('arguments', [])
            if len(values) > 2 or any(not s.isascii() or '\0' in s for s in values):
                p.error('Batch arguments must be at most two ASCII strings without NUL')
            arguments.append('    {' + ', '.join([*(json.dumps(v) for v in values), '0'] ) + '},\n')
        header.write_text('static const char *const names[] = {\n' +
                          ''.join('    "' + n + '",\n' for n in names) + '    0\n};\n' +
                          'static const char *const test_args[][3] = {\n' + ''.join(arguments) + '};\n')
        cmd = [sys.executable, str(tc / 'bin/nextstep-gcc'), '--sdk', str(sdk),
               '-arch', arch, '-O2', '--compat-headers', str(out / 'native-headers'),
               '-nodefaultlibs', '-I', str(out / arch), str(HERE / 'batch.c'),
               str(tc / 'lib' / arch / 'libgcc.a'), str(sdk / 'lib/libsys_s.a'),
               '-o', str(out / arch / 'api-batch')]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        (out / arch / 'batch-build.log').write_bytes(r.stdout + r.stderr)
        if r.returncode:
            raise SystemExit('Batch build failed: ' + arch)
        (out / arch / 'run.sh').write_text('#!/bin/sh\ncd /\n./api-batch > /api-results.txt 2>&1\nsync\n/usr/etc/halt\n')
    logs = {}
    for item in a.guest_log:
        arch, sep, filename = item.partition('=')
        if not sep or arch not in record['results'] or arch in logs:
            p.error('--guest-log needs one known ARCH=FILE per architecture')
        path = Path(filename).resolve()
        text = path.read_text()
        try:
            matches = parse_guest(text, {mode + '-' + name
                for mode, data in record['results'][arch].items()
                for name, result in data['tests'].items() if result['build'] == 'passed'})
        except ValueError as error:
            p.error(arch + ': ' + str(error))
        for name, code, sig in matches:
            mode, name = name.split('-', 1)
            result = record['results'][arch][mode]['tests'][name]
            result.update(run='passed' if int(code) == 0 and int(sig) == 0 else 'failed',
                          exit=int(code), signal=int(sig))
        logs[arch] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'path': str(path)}
    record['guest_logs'] = logs
    classify(record, out)
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    render(record, out / 'coverage.md')
    print('Ledger:', out / 'coverage.md')



def parse_guest(text, expected):
    matches = re.findall(r'^API RESULT ([a-z0-9_-]+) exit (-?\d+) signal (\d+)$', text, re.M)
    if (text.count('API BEGIN\n') != 1 or text.count('API END ') != 1 or
            len(matches) != len(expected) or {m[0] for m in matches} != expected):
        raise ValueError('Incomplete, duplicate or unexpected guest results')
    for _, code, sig in matches:
        code, sig = int(code), int(sig)
        if (sig == 0 and not 0 <= code <= 255) or (sig != 0 and code != -1):
            raise ValueError('Inconsistent exit/signal status')
    end = re.search(r'^API END (\d+) tests (\d+) failures$', text, re.M)
    failures = sum(int(code) != 0 or int(sig) != 0 for _, code, sig in matches)
    if not end or int(end[1]) != len(expected) or int(end[2]) != failures:
        raise ValueError('Guest summary does not match individual results')
    return matches


def classify(record, out):
    triage = json.loads((HERE / 'triage.json').read_text())
    triage_source = 'triage.json'
    for followup in [HERE / 'fixes-triage.json', HERE / 'expanded-triage.json']:
        if followup.is_file() and record.get('guest_logs'):
            candidate = json.loads(followup.read_text())
            if all(value['sha256'] == candidate.get('reviewed_guest_logs_sha256', {}).get(arch)
                   for arch, value in record['guest_logs'].items()):
                triage = candidate
                triage_source = followup.name
    for arch, modes in record['results'].items():
        for mode, data in modes.items():
            for entry in data['interfaces']:
                entry['classification'] = 'untested'
                if entry['link'] == 'failed':
                    log = (out / arch / mode / (entry['name'] + '-link.log')).read_text()
                    symbols = re.findall(r'^(_[A-Za-z0-9_]+)$', log, re.M)
                    if symbols == ['_' + entry['name']]:
                        entry['classification'] = 'partially supported' if entry.get('macro') else 'missing'
                for observation in triage['observations']:
                    if entry['name'] not in observation['interfaces'] or mode not in observation['modes']:
                        continue
                    if arch not in observation.get('arches', record['results']):
                        continue
                    # Curated diagnosis applies only to the exact reviewed evidence.
                    if record['guest_logs'].get(arch, {}).get('sha256') != triage.get('reviewed_guest_logs_sha256', {}).get(arch):
                        continue
                    if not any(data['tests'][test]['run'] != 'untested'
                               for test in observation['evidence_tests']):
                        continue
                    entry['classification'] = observation['classification']
                    entry['behavior'] = 'passed' if observation['classification'].startswith('working') else 'failed'
                    entry['evidence'] = observation['note']
    record['triage'] = triage
    record['triage_source'] = triage_source


def render(record, dest):
    arches = list(record['results'])
    lines = ['# API coverage', '',
             'C library and selected POSIX inventory. This is not a conformance claim.', '',
             'D/L = declaration/link availability: Y present, N probe failed. A failed',
             'probe needs diagnostic review; a successful link does not validate its ABI.',
             'Native mode retains compiler runtime and SDK syntax repairs, but excludes',
             'NextStepCompat headers and libraries. Compiler built-ins are disabled.', '',
             '## Availability', '',
             '| Interface | Standard | ' + ' | '.join(a + ' native / compat' for a in arches) + ' |',
             '| --- | --- | ' + ' | '.join('---' for _ in arches) + ' |']
    first = record['results'][arches[0]]['native']['interfaces']
    for i, api in enumerate(first):
        cells = []
        for arch in arches:
            values = []
            for mode in ('native', 'compat'):
                entry = record['results'][arch][mode]['interfaces'][i]
                values.append(('Y' if entry['declaration'] == 'present' else 'N') + '/' +
                              ('Y' if entry['link'] == 'present' else 'N') +
                              (' (macro)' if entry.get('macro') else ''))
            cells.append(' ; '.join(values))
        lines.append('| `' + api['name'] + '` | ' + api['standard'] + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Upstream behavior tests', '',
              'Each cell is native / compat. Build failure and untested are distinct',
              'from runtime failure. A failed multi-interface test does not establish',
              'which interface is at fault. Passing is limited to the selected cases.', '',
              '| Test | Host control | ' + ' | '.join(arches) + ' |',
              '| --- | --- | ' + ' | '.join('---' for _ in arches) + ' |']
    for name, host in record['host_controls'].items():
        cells = []
        for arch in arches:
            values = []
            for mode in ('native', 'compat'):
                t = record['results'][arch][mode]['tests'].get(name)
                values.append('not scheduled' if t is None else 'build failed' if t['build'] != 'passed' else t['run'])
            cells.append(' / '.join(values))
        lines.append('| ' + name + ' | ' + ('guest-only' if host.get('scope') == 'guest-only' else 'passed' if host.get('exit') == 0 else 'failed') + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', 'Upstream libc-test commit: `' + record['upstream_commit'] + '`.',
              'Machine-readable results and full diagnostics accompany this generated report.', '',
              '## Reviewed behavior and next steps', '',
              'These observations refer to the exact log hashes in ' + record.get('triage_source', 'triage.json') + '.',
              'New runs require review before inheriting a behavioral diagnosis.', '']
    for observation in record['triage']['observations']:
        lines.append('- ' + ', '.join('`' + n + '`' for n in observation['interfaces']) +
                     ': ' + observation['note'])
    lines += ['', 'Classification counts (individual interfaces, not test assertions):', '']
    from collections import Counter
    for arch, modes in record['results'].items():
        for mode, data in modes.items():
            counts = Counter(e['classification'] for e in data['interfaces'])
            lines.append('- ' + arch + ' ' + mode + ': ' +
                         ', '.join(str(count) + ' ' + name for name, count in sorted(counts.items())))
    lines += ['', *('- ' + step for step in record['triage']['next_batches']), '']
    dest.write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
