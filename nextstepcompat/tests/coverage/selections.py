"""Explicit test selections; never edit pinned upstream inputs."""
from pathlib import Path
import shutil
from calendar_vectors import generate

LOCAL_TESTS = ('memory_boundaries', 'stdio_boundaries', 'portable_apis', 'environment_time', 'time_calendar')


def prepare(here: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    original = (here / 'upstream/src/functional/string.c').read_text()
    anchor = '\tmemset(b, \'x\', sizeof b);\n\tTEST(i, strlcpy(b, "abc", sizeof b - 1)'
    if original.count(anchor) != 1 or original.count('\treturn t_status;') != 1:
        raise ValueError('Upstream string selection anchors changed')
    start = original.index(anchor)
    end = original.index('\treturn t_status;', start)
    # All C assertions remain byte-for-byte; only the trailing BSD extension
    # block is omitted. The full mixed test remains scheduled independently.
    (output / 'string_iso.c').write_text(original[:start] + original[end:])
    for name in LOCAL_TESTS:
        shutil.copyfile(here / (name + '.c'), output / (name + '.c'))
    generate(output / 'time-vectors.h')


def sources(here: Path, output: Path, name: str):
    if name == 'string_iso':
        return [output / 'selected/string_iso.c', here / 'harness.c']
    if name in LOCAL_TESTS:
        return [output / 'selected' / (name + '.c')]
    result = [here / 'upstream/src/functional' / (name + '.c'), here / 'harness.c']
    if name == 'qsort':
        result.append(here / 'upstream/src/common/rand.c')
    return result
