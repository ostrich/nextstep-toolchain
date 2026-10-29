"""Streaming UNIX compress (.Z) encoder, block mode, 16-bit dictionary.

A full dictionary emits CLEAR and starts a new packing group.
Width transitions follow compress's eight-code packing groups.
"""


def compress(source, destination):
    destination.write(b"\x1f\x9d\x90")
    dictionary = {}
    next_code = 257
    width = 9
    bits = 0
    packed = 0
    group_codes = 0

    def emit(code, final=False):
        nonlocal width, bits, packed, group_codes
        packed |= code << bits
        bits += width
        group_codes += 1
        if group_codes == 8:
            destination.write(packed.to_bytes(width, "little"))
            packed = bits = group_codes = 0
        if width < 16 and next_code > (1 << width) - 1:
            if group_codes:
                destination.write(packed.to_bytes(width, "little"))
                packed = bits = group_codes = 0
            width += 1
        if final and bits:
            destination.write(packed.to_bytes((bits + 7) // 8, "little"))

    prefix = None
    while chunk := source.read(131072):
        for byte in chunk:
            if prefix is None:
                prefix = byte
                continue
            key = (prefix << 8) | byte
            found = dictionary.get(key)
            if found is not None:
                prefix = found
            else:
                emit(prefix)
                if next_code < 65536:
                    dictionary[key] = next_code
                    next_code += 1
                else:
                    emit(256)
                    if group_codes:
                        destination.write(packed.to_bytes(width, "little"))
                    packed = bits = group_codes = 0
                    dictionary.clear()
                    next_code = 257
                    width = 9
                prefix = byte
    if prefix is not None:
        emit(prefix, final=True)


def decompress(source, destination, limit=8 * 1024**3):
    """Decode UNIX compress streams with bounded dictionaries and output."""
    header = source.read(3)
    if len(header) != 3 or header[:2] != b"\x1f\x9d" or header[2] & 0x60:
        raise ValueError("Invalid UNIX compress header")
    maximum = header[2] & 31
    if not 9 <= maximum <= 16:
        raise ValueError("Unsupported UNIX compress dictionary width")
    block_mode = bool(header[2] & 128)
    next_code = 257 if block_mode else 256
    dictionary = [bytes([i]) for i in range(256)] + [b""] * (65536 - 256)
    width = 9
    group = b""
    index = 8
    previous = None
    total = 0

    def code():
        nonlocal group, index
        if index >= 8:
            group = source.read(width)
            index = 0
        if (index + 1) * width > len(group) * 8:
            return None
        result = (int.from_bytes(group, "little") >> (index * width)) & (
            (1 << width) - 1
        )
        index += 1
        return result

    while True:
        if width < maximum and next_code > (1 << width) - 1:
            width += 1
            index = 8
        value = code()
        if value is None:
            break
        if block_mode and value == 256:
            width = 9
            next_code = 257
            previous = None
            index = 8
            continue
        if value < next_code and dictionary[value]:
            word = dictionary[value]
        elif value == next_code and previous is not None:
            word = previous + previous[:1]
        else:
            raise ValueError("Invalid UNIX compress dictionary code")
        total += len(word)
        if total > limit:
            raise ValueError("Decompressed payload exceeds the configured size limit")
        destination.write(word)
        if previous is not None and next_code < (1 << maximum):
            dictionary[next_code] = previous + word[:1]
            next_code += 1
        previous = word
    return total
