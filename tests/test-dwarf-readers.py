#!/usr/bin/env python3
"""Exercise the patched classic linker CU reader under ASan and UBSan."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Prepared, patched cctools source')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    harness = output / 'reader.c'
    harness.write_text(r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "debugcompunit.h"
static const uint8_t abbrev[] = {1,17,0,3,8,27,8,16,23,0,0,0};
static const uint8_t info[] = {
  20,0,0,0, 4,0, 0,0,0,0, 4,1,
  't','.','c',0, '.',0, 0,0,0,0, 0,0
};
static int call(const uint8_t *i, size_t ni, const uint8_t *a, size_t na)
{
    const char *name, *dir;
    uint64_t line;
    return read_comp_unit(i, ni, a, na, 1, &name, &dir, &line);
}
int main(void)
{
    size_t n;
    unsigned count = 0;
    if (!call(info, sizeof info, abbrev, sizeof abbrev)) return 1;
    for (n=0; n<sizeof info; ++n) {
        uint8_t *copy = malloc(n ? n : 1);
        memcpy(copy, info, n);
        if (call(copy, n, abbrev, sizeof abbrev)) return 2;
        free(copy); ++count;
    }
    for (n=0; n<sizeof abbrev; ++n) {
        uint8_t *copy = malloc(n ? n : 1);
        memcpy(copy, abbrev, n);
        (void)call(info, sizeof info, copy, n);
        free(copy); ++count;
    }
    for (n=0; n<sizeof info; ++n) {
        unsigned value;
        for (value=0; value<256; ++value) {
            uint8_t copy[sizeof info];
            memcpy(copy, info, sizeof copy);
            copy[n] = value;
            (void)call(copy, sizeof copy, abbrev, sizeof abbrev);
            ++count;
        }
    }
    printf("reader cases: %u\n", count);
    return 0;
}
''')
    command = ['clang', '-O1', '-g', '-fsanitize=address,undefined',
               '-fno-sanitize-recover=all', '-I' + str(source / 'ld'),
               '-I' + str(source / 'include'), str(harness),
               str(source / 'ld/debugcompunit.c'), '-o', str(output / 'reader')]
    subprocess.run(command, check=True)
    result = subprocess.run([str(output / 'reader')], capture_output=True, timeout=60)
    (output / 'run.log').write_bytes(result.stdout + result.stderr)
    (output / 'results.json').write_text(json.dumps({'command': command,
        'exit_code': result.returncode, 'passed': result.returncode == 0}, indent=2) + '\n')
    print((result.stdout + result.stderr).decode(errors='replace'))
    return 0 if result.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
