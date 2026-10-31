#!/usr/bin/env python3
"""Prepare narrowly fixed private SDK headers without changing the originals."""
import argparse
import hashlib
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--header-policy-version', action='version', version='1',
                   help=argparse.SUPPRESS)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'work/sdk-compat')
    p.add_argument('--compat-headers', type=Path,
                   help='NextStepCompat headers supplying shared application policy')
    args = p.parse_args()
    sdk = args.sdk.resolve()
    source = sdk / 'usr/include/objc/error.h'
    if not source.is_file():
        raise SystemExit('Expected original NeXT SDK objc/error.h')
    output = args.output.resolve()
    if output == sdk or sdk in output.parents:
        raise SystemExit('Compatibility headers must be outside the original SDK.')
    if (output / 'objc').is_symlink():
        raise SystemExit('Refusing a symlinked output directory.')
    # Source and installed layouts use the same component-owned policy files.
    # Copy them into the private overlay so its qualified SDK aliases also work
    # when NextStepCompat's public wrappers are not on the include path.
    support = args.compat_headers or (ROOT / 'nextstepcompat/include')
    if not args.compat_headers and not support.is_dir():
        support = ROOT.parent / 'include/nextstepcompat'
    try:
        support_bytes = {name: (support / name).read_bytes()
                         for name in ['ns33-feature-profile.h', 'ns33-fdset.h']}
    except OSError as error:
        raise SystemExit('Shared NextStepCompat headers are unavailable: ' + str(error))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in support_bytes.items():
        (output / name).write_bytes(data)
    text = source.read_text()
    fixed, count = re.subn(r'(?m)^(\s*extern\s+)_setjmp\s*\(',
                           r'\1int _setjmp(', text)
    if count != 1:
        raise SystemExit('Unexpected SDK _setjmp declaration; inspect before adapting.')
    (output / 'objc').mkdir(parents=True, exist_ok=True)
    (output / 'objc/error.h').write_text(fixed)
    fixes = [{'header': 'objc/error.h',
              'reason': 'Make the legacy implicit int return explicit.',
              'original_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'fixed_sha256': hashlib.sha256(fixed.encode()).hexdigest()}]
    class_header = sdk / 'usr/include/objc/objc-class.h'
    original = class_header.read_text()
    fixed = original
    for tag, field, outer in [('objc_ivar', 'ivar_list', 'objc_ivar_list'),
                              ('objc_method', 'method_list', 'objc_method_list')]:
        pattern = (r'(?ms)^[ \t]*struct ' + tag + r' \{(.*?)^[ \t]*\} '
                   + field + r'\[1\];')
        match = re.search(pattern, fixed)
        if not match:
            raise SystemExit('Unexpected nested SDK type ' + tag)
        body = match.group(1)
        declaration = 'struct ' + tag + ' {' + body + '};\n\n'
        fixed = fixed[:match.start()] + '\tstruct ' + tag + ' ' + field + '[1];' + fixed[match.end():]
        marker = 'struct ' + outer + ' {'
        if fixed.count(marker) != 1:
            raise SystemExit('Unexpected enclosing SDK type ' + outer)
        fixed = fixed.replace(marker, declaration + marker, 1)
    (output / 'objc/objc-class.h').write_text(fixed)
    fixes.append({'header': 'objc/objc-class.h',
                  'reason': 'Hoist C struct tags so C++ sees the same public types.',
                  'original_sha256': hashlib.sha256(class_header.read_bytes()).hexdigest(),
                  'fixed_sha256': hashlib.sha256(fixed.encode()).hexdigest()})
    fcntl = sdk / 'usr/include/bsd/sys/fcntl.h'
    original = fcntl.read_text()
    fixed, count = re.subn(r'(?m)^(\s*extern\s+)(creat|fcntl|open)\s*\(',
                           r'\1int \2(', original)
    if count != 6:
        raise SystemExit('Unexpected legacy fcntl declarations; inspect before adapting.')
    (output / 'sys').mkdir(exist_ok=True)
    (output / 'sys/fcntl.h').write_text(fixed)
    fixes.append({'header': 'sys/fcntl.h',
                  'reason': 'Make implicit int POSIX return types explicit.',
                  'original_sha256': hashlib.sha256(original.encode()).hexdigest(),
                  'fixed_sha256': hashlib.sha256(fixed.encode()).hexdigest()})
    # Public SDK entry points also use qualified names (notably fcntl.h's
    # <bsd/sys/fcntl.h>). Give every spelling the same guarded declaration.
    (output / 'bsd/sys').mkdir(parents=True, exist_ok=True)
    (output / 'bsd/sys/fcntl.h').write_text(fixed)
    fixes[-1]['aliases'] = ['bsd/sys/fcntl.h']

    def derive(relative, names, prefix, reason, transform=None):
        source = sdk / 'usr/include' / relative
        original = source.read_bytes()
        body = transform(original.decode()).encode() if transform else original
        fixed = prefix.encode() + body
        for name in names:
            destination = output / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(fixed)
        fixes.append({'header': names[0], 'aliases': names[1:],
                      'reason': reason,
                      'original_header': relative,
                      'original_sha256': hashlib.sha256(original).hexdigest(),
                      'fixed_sha256': hashlib.sha256(fixed).hexdigest()})

    # Select the component-owned user-space profile for every SDK spelling.
    # Modern-compiler syntax repairs remain here, not in NextStepCompat.
    profile = ('/* Generated user-space SDK compatibility preamble. */\n'
               '#include <ns33-feature-profile.h>\n')
    def standards_syntax(text):
        return text + ('\n#if !defined(KERNEL) && defined(__STRICT_ANSI__)\n'
                       '#undef __STRICT_ANSI__\n#define __STRICT_ANSI__ 1\n#endif\n')
    derive('ansi/standards.h', ['standards.h', 'ansi/standards.h'], profile,
           'Select the application profile and normalize the legacy compiler macro.',
           standards_syntax)
    dependencies = ('/* Generated user-space SDK compatibility preamble. */\n'
                    '#ifndef KERNEL\n#include <standards.h>\n'
                    '#include <sys/types.h>\n#endif\n')
    derive('bsd/sys/types.h', ['sys/types.h', 'bsd/sys/types.h'],
           '#ifndef KERNEL\n#include <standards.h>\n#endif\n',
           'Expose original POSIX types and the shared FD_ZERO correction.',
           lambda text: text + '\n#include <ns33-fdset.h>\n')
    def signal_prototype(text):
        # Empty () means no arguments in C23 and C++, unlike traditional C.
        # This is the POSIX callback, not the BSD sv_handler interface whose
        # extended signal arguments must remain available to legacy callers.
        text, count = re.subn(r'(?m)^([ \t]*void[ \t]+)\(\*sa_handler\)\(\);',
                             '#ifdef KERNEL\n\\1(*sa_handler)();\n#else\n'
                             '\\1(*sa_handler)(int);\n#endif', text)
        if count != 1:
            raise SystemExit('Unexpected SDK sigaction handler declaration.')
        # Keep the special handler constants compatible with signal() and
        # sigaction in C23/C++, without altering their numeric values.
        marker = '#endif /* _SYS_SIGNAL_H */'
        if text.count(marker) != 1:
            raise SystemExit('Unexpected SDK signal header guard.')
        constants = ('\n#if !defined(KERNEL) && !defined(__STRICT_BSD__)\n'
                     '#undef SIG_DFL\n#define SIG_DFL ((void (*)(int))0)\n'
                     '#undef SIG_IGN\n#define SIG_IGN ((void (*)(int))1)\n'
                     '#ifdef _NEXT_SOURCE\n#undef BADSIG\n'
                     '#define BADSIG ((void (*)(int))-1)\n#endif\n#endif\n')
        return text.replace(marker, constants + marker)

    derive('bsd/sys/signal.h', ['sys/signal.h', 'bsd/sys/signal.h'], dependencies,
           'Make signal types self-contained and prototype the POSIX callback.',
           signal_prototype)
    def ansi_signal_syntax(text):
        text, count = re.subn(r'(?m)^#define SIG_ERR[^\n]*$',
                             '#ifdef KERNEL\n#define SIG_ERR (void (*)())-1\n'
                             '#else\n#define SIG_ERR ((void (*)(int))-1)\n#endif', text)
        if count != 1:
            raise SystemExit('Unexpected SDK SIG_ERR declaration.')
        return text

    derive('ansi/signal.h', ['signal.h', 'ansi/signal.h'], dependencies,
           'Select POSIX signal declarations and type SIG_ERR for modern C/C++.',
           ansi_signal_syntax)
    derive('bsd/netinet/in.h', ['netinet/in.h', 'bsd/netinet/in.h'], dependencies,
           'Make IPv4 address types available without an earlier sys/types include.')
    derive('bsd/netdb.h', ['netdb.h', 'bsd/netdb.h'], dependencies,
           'Guard network database structures against repeated inclusion.',
           lambda text: '#ifndef NEXTSTEP_SDK_NETDB_H\n#define NEXTSTEP_SDK_NETDB_H\n'
                        + text + '\n#endif\n')
    (output / 'fixes.json').write_text(json.dumps({
        'fixes': fixes,
        'support_headers': {name: hashlib.sha256(data).hexdigest()
                            for name, data in support_bytes.items()},
    }, indent=2) + '\n')
    print('Prepared private SDK compatibility headers; originals unchanged.')

if __name__ == '__main__':
    main()
