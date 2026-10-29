#!/usr/bin/env python3
"""Retain legacy Mach-O DWARF objects beside an executable or fixed-VM library.

The classic linker emits N_OSO debug-map entries rather than linking DWARF.
This helper retains those objects and rewrites their entries to paths relative
to the executable. GDB needs the port's relative-OSO reader patch.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile


def bundle(executable, directory, relative_prefix, expected_filetype=2):
    data = bytearray(executable.read_bytes())
    if data[:4] == b'\xce\xfa\xed\xfe':
        endian = '<'
    elif data[:4] == b'\xfe\xed\xfa\xce':
        endian = '>'
    else:
        raise ValueError('Expected a thin 32-bit Mach-O image')
    if len(data) < 28:
        raise ValueError('Truncated Mach-O header')
    _, cpu, _, filetype, ncmds, sizeofcmds, _ = struct.unpack_from(endian + '7I', data)
    if expected_filetype not in (2, 3) or filetype != expected_filetype or 28 + sizeofcmds > len(data):
        raise ValueError('Expected a complete MH_EXECUTE or requested MH_FVMLIB header')
    original_size = len(data)
    position, symtab, linkedit = 28, None, None
    for _ in range(ncmds):
        if position + 8 > 28 + sizeofcmds:
            raise ValueError('Truncated load command')
        command, size = struct.unpack_from(endian + '2I', data, position)
        if size < 8 or position + size > 28 + sizeofcmds:
            raise ValueError('Invalid load command length')
        if command == 1:
            if size < 56:
                raise ValueError('Truncated segment command')
            if bytes(data[position + 8:position + 24]).rstrip(b'\0') == b'__LINKEDIT':
                linkedit = position
        if command == 2:
            if size != 24 or symtab is not None:
                raise ValueError('Invalid or duplicate symbol table command')
            symtab = position
        if command == 11:
            if size < 80 or struct.unpack_from(endian + 'I', data, position + 44)[0]:
                raise ValueError('Dynamic module string tables are not supported')
        position += size
    if symtab is None or position != 28 + sizeofcmds:
        raise ValueError('Missing symbol table or inconsistent load command size')
    symoff, nsyms, stroff, strsize = struct.unpack_from(endian + '4I', data, symtab + 8)
    if (symoff < position or symoff + nsyms * 12 > stroff
            or stroff + strsize > len(data)
            or any(data[stroff + strsize:])):
        raise ValueError('Expected a terminal string table and bounded symbols')
    strings = bytes(data[stroff:stroff + strsize])
    newstrings = bytearray(b'\0' * 4)
    names = {b'': 0}
    objects = {}
    replacements = {}
    source_cache = {}
    for index in range(nsyms):
        offset = symoff + index * 12
        strx, kind, _, _, timestamp = struct.unpack_from(endian + 'IBBHI', data, offset)
        if strx >= strsize:
            raise ValueError('Symbol string offset out of bounds')
        end = strings.find(b'\0', strx)
        if end < 0:
            raise ValueError('Unterminated symbol name')
        name = strings[strx:end]
        if kind == 0x66 and name:  # N_OSO
            text = os.fsdecode(name)
            member = ''
            if text.endswith(')') and '(' in text:
                text, member = text.rsplit('(', 1)
                member = '(' + member
            original = Path(text)
            if not original.is_absolute():
                original = executable.parent / original
            if not original.is_file():
                raise ValueError('A referenced debug object is unavailable')
            stat = original.stat()
            # An archive OSO timestamp describes its member, not the file.
            if not member and timestamp and int(stat.st_mtime) != timestamp:
                raise ValueError('A referenced debug object timestamp has changed')
            if original not in source_cache:
                source_cache[original] = hashlib.sha256(original.read_bytes()).hexdigest()
            sha = source_cache[original]
            if (len(original.stem) == 64
                    and all(c in '0123456789abcdef' for c in original.stem)
                    and original.stem != sha):
                raise ValueError('Content-addressed source object has changed')
            filename = sha + ('.a' if member else '.o')
            target = directory / filename
            objects[filename] = {'sha256': sha, 'size': stat.st_size,
                                 'mtime': int(target.stat().st_mtime) if target.exists() else int(stat.st_mtime)}
            struct.pack_into(endian + 'I', data, offset + 8,
                             timestamp if member else objects[filename]['mtime'])
            replacements[target] = original
            name = os.fsencode(relative_prefix.rstrip('/') + '/' + filename + member)
        if name not in names:
            names[name] = len(newstrings)
            newstrings += name + b'\0'
        struct.pack_into(endian + 'I', data, offset, names[name])
    if not objects:
        return {'schema': 1, 'cpu': cpu, 'objects': {}, 'status': 'no_debug_map',
                'executable_sha256': hashlib.sha256(data).hexdigest()}
    newstrings += b'\0' * (-len(newstrings) % 4)
    newsize = max(original_size, stroff + len(newstrings))
    if newsize > original_size:
        if linkedit is None:
            raise ValueError('Growing a debug map requires a link-edit segment')
        _, vmsize, fileoff, filesize = struct.unpack_from(endian + '4I', data, linkedit + 24)
        if fileoff + filesize != original_size or newsize - fileoff > vmsize:
            raise ValueError('Debug map exceeds the reserved link-edit mapping')
        struct.pack_into(endian + 'I', data, linkedit + 36, newsize - fileoff)
    # Finish all validation before retaining objects or replacing executable.
    directory.mkdir(parents=True, exist_ok=True)
    for target, original in replacements.items():
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != target.stem:
                raise ValueError('Existing retained object has unexpected contents')
        else:
            shutil.copy2(original, target)
            target.chmod(0o644)
    data = data[:stroff] + newstrings
    data += b'\0' * (newsize - len(data))
    struct.pack_into(endian + 'I', data, symtab + 20, len(newstrings))
    descriptor, temporary_name = tempfile.mkstemp(prefix='.nextstep-debug-', dir=executable.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        temporary.chmod(executable.stat().st_mode & 0o777)
        temporary.replace(executable)
    finally:
        temporary.unlink(missing_ok=True)
    return {'schema': 1, 'cpu': cpu, 'objects': objects,
            'executable_sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--relative-prefix', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    prefix = Path(args.relative_prefix)
    if prefix.is_absolute() or '..' in prefix.parts:
        parser.error('The debug object prefix must be relative without parent traversal')
    try:
        result = bundle(args.executable, args.directory, args.relative_prefix)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    args.manifest.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
