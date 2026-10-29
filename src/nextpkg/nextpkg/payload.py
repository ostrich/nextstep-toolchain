"""Explicit payload metadata and native NeXT content checksums."""

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import stat
import struct


@dataclass
class Entry:
    path: str
    kind: str
    mode: int
    uid: int = 0
    gid: int = 0
    mtime: int = 0
    source: Path | None = None
    target: str = ""
    size: int = 0
    checksum: int = 0
    slices: list = field(default_factory=list)


def checksum(stream, offset=0, size=None):
    stream.seek(offset)
    if size is None:
        stream.seek(0, 2)
        size = stream.tell() - offset
        stream.seek(offset)
    if size < 4:
        return int.from_bytes(stream.read(size), "little")
    result = 0
    left = size
    tail = b""
    while left:
        chunk = stream.read(min(131072, left))
        if not chunk:
            raise ValueError("File became shorter while checksumming")
        tail = (tail + chunk)[-4:]
        full = len(chunk) // 4 * 4
        result += sum(item[0] for item in struct.iter_unpack(">I", chunk[:full]))
        left -= len(chunk)
    if size % 4:
        result += int.from_bytes(tail, "big")
    return result & 0xFFFFFFFF


def check_image_mode(header, mode, path):
    """Classic fixed-VM libraries are executable images, not ordinary data."""
    if len(header) < 16 or header[:4] not in (b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xce"):
        return
    endian = "<" if header[:4] == b"\xce\xfa\xed\xfe" else ">"
    filetype = struct.unpack_from(endian + "I", header, 12)[0]
    if filetype == 3 and not mode & 0o111:  # MH_FVMLIB
        raise ValueError(f"{path}: fixed-VM shared library requires execute permission")


def scan_file(entry):
    entry.size = entry.source.stat().st_size
    if entry.size > 0xFFFFFFFF:
        raise ValueError(f"{entry.path}: file exceeds the 32-bit package format")
    with entry.source.open("rb") as stream:
        entry.checksum = checksum(stream, size=entry.size)
        stream.seek(0)
        header = stream.read(28)
        check_image_mode(header, entry.mode, entry.path)
        # Java class files share CAFEBABE with fat Mach-O. Their version
        # occupies the would-be architecture-count field.
        if (
            header[:4] == b"\xca\xfe\xba\xbe"
            and len(header) >= 8
            and struct.unpack_from(">H", header, 4)[0] in (0, 65535)
            and 45 <= struct.unpack_from(">H", header, 6)[0] <= 100
        ):
            return
        if header[:4] in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
            endian = ">" if header[:4] == b"\xca\xfe\xba\xbe" else "<"
            count = struct.unpack_from(endian + "I", header, 4)[0]
            if not 1 <= count <= 64:
                raise ValueError(f"{entry.path}: invalid fat Mach-O architecture count")
            stream.seek(8)
            table = stream.read(count * 20)
            if len(table) != count * 20:
                raise ValueError(f"{entry.path}: truncated fat Mach-O table")
            ranges = []
            for i in range(count):
                cpu, subtype, offset, size, align = struct.unpack_from(
                    endian + "iiIII", table, i * 20
                )
                if (
                    offset < 8 + count * 20
                    or not size
                    or offset + size > entry.size
                    or align > 31
                    or offset % (1 << align)
                ):
                    raise ValueError(f"{entry.path}: invalid fat Mach-O slice")
                if any(offset < end and start < offset + size for start, end in ranges):
                    raise ValueError(f"{entry.path}: overlapping fat Mach-O slices")
                ranges.append((offset, offset + size))
                stream.seek(offset)
                check_image_mode(stream.read(min(size, 28)), entry.mode, entry.path)
                entry.slices.append(
                    (cpu, subtype, size, checksum(stream, offset, size))
                )
        elif header[:4] in (b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xce"):
            endian = "<" if header[:4] == b"\xce\xfa\xed\xfe" else ">"
            cpu, subtype = struct.unpack_from(endian + "ii", header, 4)
            entry.slices.append((cpu, subtype, entry.size, entry.checksum))


def make_bom(entries, extra_archs=()):
    from .bom import Builder

    builder = Builder()
    inodes = {}
    next_inode = 10
    for entry in entries:
        if entry.kind != "hardlink":
            inodes[entry.path] = next_inode
            next_inode += 1
    main, links = [], []
    groups = {}
    for entry in entries:
        if entry.kind == "hardlink":
            groups.setdefault(entry.target, [entry.target]).append(entry.path)
    totals = {(-1, -1): 0}
    for cpu, subtype in extra_archs:
        totals[cpu, subtype] = 0
    for entry in entries:
        if entry.kind == "hardlink":
            continue
        inode = inodes[entry.path]
        if entry.path == ".":
            key = struct.pack(">I", 1) + b"."
        else:
            parent = str(PurePosixPath(entry.path).parent)
            key = (
                struct.pack(">I", inodes[parent])
                + PurePosixPath(entry.path).name.encode()
            )
        kind_mode = {
            "file": stat.S_IFREG,
            "directory": stat.S_IFDIR,
            "symlink": stat.S_IFLNK,
        }[entry.kind]
        value = struct.pack(
            ">HHHII", kind_mode | entry.mode, entry.uid, entry.gid, entry.mtime, inode
        )
        if entry.kind == "directory":
            value += struct.pack(">I", 1024)
            totals[-1, -1] += 1024
        elif entry.kind == "symlink":
            value += entry.target.encode() + b"\0"
            totals[-1, -1] += len(entry.target.encode())
        else:
            value += struct.pack(">II", entry.size, entry.checksum)
            if entry.slices:
                value += struct.pack(">I", len(entry.slices))
                for cpu, subtype, size, csum in entry.slices:
                    value += struct.pack(">iiII", cpu, subtype, size, csum)
                    totals[cpu, subtype] = totals.get((cpu, subtype), 0) + size
            elif entry.slices:
                cpu, subtype, size, csum = entry.slices[0]
                totals[cpu, subtype] = totals.get((cpu, subtype), 0) + size
            else:
                totals[-1, -1] += entry.size
        main.append((key, value))
    for master, paths in groups.items():
        for i, path in enumerate(paths):
            links.append(
                (
                    ("./" + path).encode(),
                    bytes([int(i == 0)])
                    + ("./" + paths[(i + 1) % len(paths)]).encode()
                    + b"\0",
                )
            )

    def directory(rows):
        return [
            (name.encode() + b"\0", struct.pack(">I", block) + cls.encode() + b"\0")
            for name, block, cls in rows
        ]

    builder.tree(1, directory([("DefaultUnixBTree", 2, "UnixBTree")]))
    builder.tree(
        2,
        directory(
            [
                ("Main", 3, "IXBTree"),
                ("Links", 4, "IXBTree"),
                ("MiscInfo", 5, "IXBTree"),
                ("Architecture Extras Directory", 6, "IXStoreDirectory"),
                ("Architecture Exceptions Directory", 7, "IXStoreDirectory"),
                ("Language Extras Directory", 8, "IXStoreDirectory"),
                ("Language Exceptions Directory", 9, "IXStoreDirectory"),
            ]
        ),
    )
    builder.tree(3, main)
    builder.tree(4, links)
    if any(size > 0xFFFFFFFF for size in totals.values()):
        raise ValueError(
            "BOM architecture byte totals exceed 32 bits; split this package"
        )
    arch_info = struct.pack(">I", len(totals)) + b"".join(
        struct.pack(">iiII", cpu, subtype, size, 0)
        for (cpu, subtype), size in sorted(totals.items())
    )
    builder.tree(
        5,
        [
            (b"BOM Format Version", b"1\0"),
            (b"BOM Next Fake Inode", str(next_inode).encode() + b"\0"),
            (b"BOM Content Size", str(sum(totals.values())).encode() + b"\0"),
            (b"BOM Archs Info", arch_info),
        ],
    )
    for i in range(6, 10):
        builder.tree(i, [])
    return builder.finish()
