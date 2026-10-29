"""NeXT binary BOM storage, independently implemented from native fixtures."""

import struct


class FormatError(ValueError):
    pass


def u16(data, offset=0):
    return struct.unpack_from(">H", data, offset)[0]


def u32(data, offset=0):
    return struct.unpack_from(">I", data, offset)[0]


class Store:
    def __init__(self, data):
        self.data = data
        if (
            len(data) < 8192
            or data[28:32] not in (b"allo", b"NeXT")
            or u32(data, 20) != 0x4249
        ):
            raise FormatError("Not a supported NeXT IXStore BOM")
        if data[16] & 0x40:
            raise FormatError("Shadowed IXStore files are not supported")
        self.index = 48 + u32(data, 44)
        if self.index + 16 > len(data):
            raise FormatError("Truncated IXStore index")
        self.count = u32(data, self.index + 8)
        capacity = u32(data, self.index)
        if (
            self.count < 2
            or self.count * 8 > capacity
            or self.index + 16 + capacity > len(data)
        ):
            raise FormatError("Invalid IXStore index capacity")

    def block(self, identifier):
        if not 0 < identifier < self.count:
            raise FormatError(f"Invalid storage block number {identifier}")
        pointer, flags = struct.unpack_from(
            ">II", self.data, self.index + 16 + identifier * 8
        )
        if flags & 0x70000000:
            raise FormatError("Unsupported indirect or deleted IXStore block")
        page, index = pointer & ~8191, pointer & 8191
        if not page or not index:
            raise FormatError(f"Missing storage block {identifier}")
        if flags & 0x80000000:
            size = index * 8192
            if page + size > len(self.data):
                raise FormatError("Truncated directly mapped IXStore block")
            return self.data[page : page + size]
        if page + 8192 > len(self.data):
            raise FormatError("Truncated IXStore clump")
        count = u16(self.data, page + 30)
        if 36 + count * 12 > 8192:
            raise FormatError("Invalid IXStore clump entry count")
        for entry in range(page + 36, page + 36 + count * 12, 12):
            slot, identity = struct.unpack_from(">II", self.data, entry)
            if slot & 65535 == index:
                offset, size = struct.unpack_from(">HH", self.data, entry + 8)
                if (
                    identity != identifier
                    or offset < 36 + count * 12
                    or offset + size > 8192
                ):
                    raise FormatError(f"Invalid storage block {identifier}")
                return self.data[page + offset : page + offset + size]
        raise FormatError(f"Missing IXStore clump slot for block {identifier}")

    def tree(self, identifier):
        visited = set()

        def walk(identifier, expected=None):
            if identifier in visited:
                raise FormatError("Cycle or repeated node in IXBTree")
            visited.add(identifier)
            data = self.block(identifier)
            if len(data) < 38:
                raise FormatError("Truncated IXBTree node")
            depth = u32(data, 8)
            if depth > 16 or (expected is not None and depth != expected):
                raise FormatError("Invalid IXBTree depth")
            node = data[16:]
            result = []
            if depth:
                count = u16(node, 10)
                if u16(node, 6) != len(node) or u16(node, 8) > len(node):
                    raise FormatError("Invalid IXBTree branch capacity")
                if 16 + count * 4 > len(node):
                    raise FormatError("Truncated IXBTree branch")
                children = [u32(node, 12) >> 13] + [
                    u32(node, 16 + 4 * i) >> 13 for i in range(count)
                ]
                for child in children:
                    result.extend(walk(child, depth - 1))
            else:
                count = u16(node, 18)
                if u16(node, 8) != len(node) or u16(node, 10) > len(node):
                    raise FormatError("Invalid IXBTree leaf capacity")
                if 20 + count * 2 > len(node):
                    raise FormatError("Truncated IXBTree leaf")
                for i in range(count):
                    offset = u16(node, 20 + i * 2)
                    if offset < 20 + count * 2 or offset + 4 > len(node):
                        raise FormatError("Invalid IXBTree record offset")
                    key_flags, value_size = struct.unpack_from(">HH", node, offset)
                    if key_flags & 0x4000:
                        raise FormatError("External IXBTree values are not supported")
                    key_size = (key_flags >> 1) & 8191
                    end = offset + 4 + key_size + value_size
                    if end > len(node):
                        raise FormatError("Truncated IXBTree record")
                    result.append(
                        (
                            node[offset + 4 : offset + 4 + key_size],
                            node[offset + 4 + key_size : end],
                        )
                    )
            return result

        return walk(identifier)

    def directory(self, identifier):
        return {
            key.rstrip(b"\0").decode(): (u32(value), value[4:].rstrip(b"\0").decode())
            for key, value in self.tree(identifier)
        }


def leaf(identifier, records, size=8192):
    """Encode a compact, uncompressed IXBTree leaf node."""
    records = sorted(records)
    data = bytearray(size)
    struct.pack_into(">4I", data, 0, 0, identifier, 0, 1)
    end = size - 16
    used = 22 + len(records) * 2
    for i, (key, value) in enumerate(records):
        record = struct.pack(">HH", len(key) * 2, len(value)) + key + value
        end -= len(record)
        if end < 22 + len(records) * 2:
            raise FormatError("Tree exceeds one leaf")
        data[16 + end : 16 + end + len(record)] = record
        struct.pack_into(">H", data, 36 + i * 2, end)
        used += len(record)
    struct.pack_into(">IHHHHII", data, 16, 0, 0, end, size - 16, used, 0, len(records))
    return bytes(data)


def write_store(blocks):
    """Canonical unshadowed IXStore with directly mapped 8 KiB blocks."""
    count = len(blocks)
    header_size = (0x810 + (count + 1) * 8 + 8191) & ~8191
    data = bytearray(header_size + count * 8192)
    struct.pack_into(">I", data, 20, 0x4249)
    data[28:32] = b"allo"
    struct.pack_into(">4I", data, 32, len(data), 0, 1, 2000)
    struct.pack_into(">4I", data, 0x800, header_size - 0x810, 0, count + 1, 0)
    for identifier in range(1, count + 1):
        offset = header_size + (identifier - 1) * 8192
        block = blocks[identifier]
        if len(block) != 8192:
            raise FormatError("Expected 8 KiB storage block")
        struct.pack_into(">II", data, 0x810 + identifier * 8, offset | 1, 0x80000000)
        data[offset : offset + 8192] = block
    return bytes(data)


class Builder:
    """Bulk-load balanced IXBTrees; does not reuse native binary templates."""

    def __init__(self):
        self.blocks = {}
        self.next_id = 10

    def reserve(self):
        result = self.next_id
        self.next_id += 1
        return result

    def tree(self, root, records):
        records = sorted(records)
        groups, group, used = [], [], 38
        for key, value in records:
            cost = 6 + len(key) + len(value)
            if used + cost > 8192:
                if not group:
                    raise FormatError("BOM record is too large for an IXBTree node")
                groups.append(group)
                group, used = [], 38
            group.append((key, value))
            used += cost
        groups.append(group)
        if len(groups) == 1:
            self.blocks[root] = leaf(root, groups[0])
            return
        children = []
        for group in groups:
            identifier = self.reserve()
            self.blocks[identifier] = leaf(identifier, group)
            children.append((group[0][0], identifier))
        depth = 1
        while True:
            levels, group, used = [], [], 36
            for child in children:
                cost = 0 if not group else len(child[0]) + 6
                if used + cost > 8192:
                    levels.append(group)
                    group, used, cost = [], 36, 0
                group.append(child)
                used += cost
            levels.append(group)
            if len(levels) == 1:
                self.blocks[root] = branch(root, levels[0], depth)
                break
            children = []
            for group in levels:
                identifier = self.reserve()
                self.blocks[identifier] = branch(identifier, group, depth)
                children.append((group[0][0], identifier))
            depth += 1

    def finish(self):
        return write_store(self.blocks)


def branch(identifier, children, depth):
    data = bytearray(8192)
    struct.pack_into(">4I", data, 0, 0, identifier, depth, 1)
    end = 8176
    used = 20 + 4 * (len(children) - 1)
    for i, (key, child) in enumerate(children[1:]):
        record = struct.pack(">H", len(key)) + key
        end -= len(record)
        data[16 + end : 16 + end + len(record)] = record
        struct.pack_into(">I", data, 32 + i * 4, (child << 13) | end)
        used += len(record)
    struct.pack_into(
        ">IHHHHI", data, 16, 0, end, 8176, used, len(children) - 1, children[0][1] << 13
    )
    return bytes(data)
