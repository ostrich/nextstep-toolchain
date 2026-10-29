"""Reproducible native Installer package generation, entirely on the host."""

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import tarfile
import tempfile
from .manifest import load, UserError, safe_path
from .payload import Entry, scan_file, make_bom, check_image_mode
from .compress import compress, decompress
from .bom import Store, u32, u16, FormatError

ARCHS = ((6, "m68k", "N"), (7, "i386", "I"), (11, "hppa", "H"), (14, "sparc", "S"))


def add_generated(entries, entry):
    safe_path(entry.path)
    if any(e.path == entry.path for e in entries):
        raise UserError(f"{entry.path}: conflicts with generated package metadata")
    from pathlib import PurePosixPath

    existing = {e.path: e for e in entries}
    for parent in reversed(PurePosixPath(entry.path).parents):
        parent = str(parent)
        if parent not in existing:
            e = Entry(parent, "directory", 0o755)
            entries.append(e)
            existing[parent] = e
        elif existing[parent].kind != "directory":
            raise UserError(
                f"{entry.path}: generated metadata parent is not a directory"
            )
    entries.append(entry)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(manifest, output, force=False, dry_run=False, progress=print):
    spec, entries = load(manifest)
    name = spec["name"]
    version = spec["version"] + "-" + str(spec["revision"])
    progress(f"{name} {version}: preparing {len(entries)} payload entries")
    with tempfile.TemporaryDirectory(prefix="nextpkg-") as temporary:
        work = Path(temporary)
        # Snapshot inputs once. Checksums and archives use the same bytes.
        for i, entry in enumerate(entries):
            if entry.kind == "file":
                staged = work / ("input-" + str(i))
                shutil.copyfile(entry.source, staged)
                entry.source = staged
        if spec.get("dependencies") or spec.get("provides"):
            deps = work / "consumer.deps"
            deps.write_text("\n".join(spec["dependencies"]) + "\n")
            add_generated(
                entries,
                Entry(
                    "usr/local/share/nextports/consumers/" + name + ".deps",
                    "file",
                    0o644,
                    source=deps,
                ),
            )
        if "readme" in spec:
            readme = work / "README.txt"
            shutil.copyfile(spec["readme"], readme)
            add_generated(
                entries,
                Entry(
                    "usr/local/share/doc/" + name + "/README.txt",
                    "file",
                    0o644,
                    source=readme,
                ),
            )
        hook_entries = []
        for role, source in spec["hooks"].items():
            staged = work / ("hook-" + role)
            shutil.copyfile(source, staged)
            spec["hooks"][role] = staged
            entry = Entry(name + "." + role, "file", 0o755, source=staged)
            scan_file(entry)
            hook_entries.append(entry)
        progress("Checking file contents and Mach-O architecture slices...")
        for entry in entries:
            if entry.kind == "file":
                scan_file(entry)
        detected = {
            cpu for entry in entries + hook_entries for cpu, _, _, _ in entry.slices
        }
        unknown = detected - {cpu for cpu, _, _ in ARCHS}
        if unknown:
            raise UserError(
                "Unsupported Mach-O CPU type(s): "
                + ", ".join(map(str, sorted(unknown)))
            )
        archs = spec.get("architectures", "auto")
        if archs == "auto":
            archs = [arch for cpu, arch, _ in ARCHS if cpu in detected]
        else:
            wanted = {cpu for cpu, arch, _ in ARCHS if arch in archs}
            if detected - wanted:
                raise UserError("architectures omits a CPU present in the payload")
            # A package advertised for an architecture must run every executable
            # there. Data archives may legitimately contain subsets.
            for entry in entries + hook_entries:
                if entry.kind == "file" and entry.mode & 0o111 and entry.slices:
                    missing = wanted - {v[0] for v in entry.slices}
                    if missing:
                        raise UserError(
                            f"{entry.path}: executable lacks an advertised architecture"
                        )
        wanted = {cpu for cpu, arch, _ in ARCHS if arch in archs}
        for entry in hook_entries:
            if entry.slices and wanted - {v[0] for v in entry.slices}:
                raise UserError(f"{entry.path}: hook lacks an advertised architecture")
        record = {
            "package": name,
            "version": version,
            "architectures": archs,
            "files": {
                e.path: {
                    "sha256": digest(e.source),
                    "mode": format(e.mode, "04o"),
                    "uid": e.uid,
                    "gid": e.gid,
                }
                for e in entries
                if e.kind == "file"
            },
            "links": {
                e.path: e.target for e in entries if e.kind in ("symlink", "hardlink")
            },
        }
        metadata = work / "BUILD.json"
        metadata.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        record_entry = Entry(
            "usr/local/share/doc/" + name + "/BUILD.json",
            "file",
            0o644,
            source=metadata,
        )
        add_generated(entries, record_entry)
        scan_file(record_entry)
        entries.sort(key=lambda e: e.path)
        suffix = "".join(code for _, arch, code in ARCHS if arch in archs)
        filename = (
            f"{name}-{version}.pkg" + ("." + suffix if suffix else "") + ".tar.gz"
        )
        if dry_run:
            progress(
                f'Valid: {len(entries)} entries; architectures: {", ".join(archs) or "architecture independent"}'
            )
            progress("Would create " + filename)
            return None
        output = output.resolve()
        archive = output / filename
        if archive.exists() and not force:
            raise UserError(
                f"{filename} already exists; increment revision or use --force to replace it"
            )
        pkg = work / (name + ".pkg")
        pkg.mkdir()
        progress("Writing native BOM and compressed payload...")
        (pkg / (name + ".bom")).write_bytes(
            make_bom(
                entries,
                [
                    (cpu, subtype)
                    for entry in hook_entries
                    for cpu, subtype, _, _ in entry.slices
                ],
            )
        )
        payload = work / "payload.tar"
        with tarfile.open(payload, "w", format=tarfile.USTAR_FORMAT) as tar:
            # Targets must precede hard links in the native extraction stream.
            for entry in sorted(entries, key=lambda e: (e.kind == "hardlink", e.path)):
                member = tarfile.TarInfo(
                    "." if entry.path == "." else "./" + entry.path
                )
                member.mode, member.uid, member.gid, member.mtime = (
                    entry.mode,
                    entry.uid,
                    entry.gid,
                    0,
                )
                if entry.kind == "directory":
                    member.type = tarfile.DIRTYPE
                elif entry.kind == "symlink":
                    member.type = tarfile.SYMTYPE
                    member.linkname = entry.target
                elif entry.kind == "hardlink":
                    member.type = tarfile.LNKTYPE
                    member.linkname = "./" + entry.target
                else:
                    member.size = entry.size
                if entry.kind == "file":
                    with entry.source.open("rb") as source:
                        tar.addfile(member, source)
                else:
                    tar.addfile(member)
        with payload.open("rb") as source, (pkg / (name + ".tar.Z")).open(
            "wb"
        ) as destination:
            compress(source, destination)
        info = {
            "Title": spec["title"],
            "Version": version,
            "Description": spec["description"],
            "DefaultLocation": spec["location"],
            "DiskName": name,
            "Relocatable": "YES" if spec.get("relocatable", False) else "NO",
            "Application": "NO",
            "LibrarySubdirectory": "Standard",
            "InstallOnly": "NO",
            "DisableStop": "YES",
            "LongFilenames": "NO",
            "NeedsAuthorization": "YES",
        }
        (pkg / (name + ".info")).write_text(
            "".join(f"{k} {v}\n" for k, v in info.items())
        )
        if "icon" in spec:
            shutil.copyfile(spec["icon"], pkg / (name + ".tiff"))
        hooks = {}
        if spec["dependencies"]:
            hooks["pre_install"] = [
                "test -r "
                + shlex.quote("/usr/local/lib/" + dep)
                + " || { echo "
                + shlex.quote("Install the runtime providing " + dep + " first.")
                + "; exit 1; }"
                for dep in spec["dependencies"]
            ]
        if spec["provides"]:
            hooks["pre_delete"] = [
                "for declaration in /usr/local/share/nextports/consumers/*.deps /usr/local/share/openstep-libs/consumers/*.deps; do",
                ' test -f "$declaration" || continue',
                ' case "$declaration" in */' + name + ".deps) continue ;; esac",
            ]
            for lib in spec["provides"]:
                hooks["pre_delete"] += [
                    " /usr/bin/fgrep -x "
                    + shlex.quote(lib)
                    + ' "$declaration" >/dev/null',
                    " result=$?",
                    ' case "$result" in 0) echo "Remove dependent packages first: $declaration"; exit 1 ;; 1) ;; *) exit 1 ;; esac',
                ]
            hooks["pre_delete"] += ["done"]
        special = [e for e in entries if e.mode & 0o6000 and e.kind == "file"]
        if special:
            hooks["post_install"] = [
                'test -n "$2" || { echo "Missing installation location"; exit 1; }'
            ]
            hooks["post_install"] += [
                "/bin/chmod "
                + format(e.mode, "04o")
                + ' "$2"/'
                + shlex.quote(e.path)
                + " || exit 1"
                for e in special
            ]
        for role in set(hooks) | set(spec["hooks"]):
            lines = ["#!/bin/sh"]
            user = spec["hooks"].get(role)
            user_lines = []
            if user:
                if role not in hooks:
                    shutil.copyfile(user, pkg / (name + "." + role))
                    continue
                text = user.read_text()
                first, separator, body = text.partition("\n")
                interpreter = (
                    shlex.split(first[2:]) if first.startswith("#!") else ["/bin/sh"]
                )
                if first.startswith("#!"):
                    text = body
                if not interpreter or Path(interpreter[0]).name not in (
                    "sh",
                    "bash",
                    "zsh",
                    "ksh",
                ):
                    raise UserError(
                        f"hooks.{role}: combining generated checks requires a Bourne-compatible shell script"
                    )
                # Inline the custom program in a subprocess. Installer copies only
                # known hook names into receipts, so a separate helper is unsafe.
                user_lines = [
                    " ".join(shlex.quote(arg) for arg in interpreter)
                    + " -c "
                    + shlex.quote(text)
                    + " "
                    + shlex.quote(name + "." + role)
                    + ' "$1" "$2" || exit $?'
                ]
            if role == "post_install":
                lines += user_lines + hooks.get(role, [])
            else:
                lines += hooks.get(role, []) + user_lines
            lines += ["exit 0"]
            (pkg / (name + "." + role)).write_text("\n".join(lines) + "\n")
        # Stable conservative 1 KiB accounting, independent of the host filesystem.
        overhead = (
            sum(
                (p.stat().st_size + 1023) // 1024
                for p in pkg.iterdir()
                if not p.name.endswith(".tar.Z")
            )
            + 4
        )
        installed = (
            sum(
                (
                    (e.size + 1023) // 1024
                    if e.kind == "file"
                    else 1 if e.kind != "hardlink" else 0
                )
                for e in entries
            )
            + overhead
        )
        compressed = sum((p.stat().st_size + 1023) // 1024 for p in pkg.iterdir()) + 4
        (pkg / (name + ".sizes")).write_text(
            f"NumFiles {len(entries)}\nInstalledSize {installed}\nCompressedSize {compressed}\n"
        )
        progress("Checking package structure, payload and BOM agreement...")
        check(pkg)
        output.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix="." + filename + ".", dir=output)
        try:
            with os.fdopen(fd, "wb") as raw, gzip.GzipFile(
                filename="", fileobj=raw, mode="wb", mtime=0
            ) as gz, tarfile.open(
                fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT
            ) as tar:
                member = tarfile.TarInfo(pkg.name)
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                tar.addfile(member)
                for item in sorted(pkg.iterdir()):
                    member = tarfile.TarInfo(pkg.name + "/" + item.name)
                    member.size = item.stat().st_size
                    member.mode = (
                        0o755
                        if any(
                            item.name.startswith(name + "." + role)
                            for role in (
                                "pre_install",
                                "post_install",
                                "pre_delete",
                                "post_delete",
                            )
                        )
                        else 0o644
                    )
                    with item.open("rb") as source:
                        tar.addfile(member, source)
                if "readme" in spec:
                    member = tarfile.TarInfo("README.txt")
                    member.size = readme.stat().st_size
                    member.mode = 0o644
                    with readme.open("rb") as source:
                        tar.addfile(member, source)
            os.chmod(temp, 0o644)
            os.replace(temp, archive)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        checksum_path = archive.with_name(archive.name + ".sha256")
        fd, checksum_temp = tempfile.mkstemp(
            prefix="." + checksum_path.name + ".", dir=output
        )
        try:
            with os.fdopen(fd, "w") as checksum_file:
                checksum_file.write(digest(archive) + "  " + archive.name + "\n")
            os.chmod(checksum_temp, 0o644)
            os.replace(checksum_temp, checksum_path)
        finally:
            if os.path.exists(checksum_temp):
                os.unlink(checksum_temp)
        progress(f"Created {archive} ({archive.stat().st_size:,} bytes)")
        return archive


def read_members(path):
    """Read metadata and spool compressed payloads without extracting paths."""
    required = ("info", "sizes", "bom", "tar.Z")
    if path.is_dir():
        name = path.name.removesuffix(".pkg")
        result = {}
        for ext in required:
            item = path / (name + "." + ext)
            if item.is_symlink():
                raise UserError("Package members must not be symlinks")
            if item.is_file():
                if ext == "tar.Z":
                    result[item.name] = item.open("rb")
                else:
                    if item.stat().st_size > 64 * 1024 * 1024:
                        raise UserError("Package metadata is too large")
                    result[item.name] = item.read_bytes()
        return name, result
    with tarfile.open(path, "r:*") as tar:
        members = {}
        package = None
        try:
            for member in tar:
                parts = Path(member.name).parts
                if len(parts) == 2 and parts[0].endswith(".pkg") and member.isfile():
                    if package is not None and package != parts[0]:
                        raise UserError("Archive contains multiple packages")
                    package = parts[0]
                    name = package[:-4]
                    if parts[1] not in {name + "." + ext for ext in required}:
                        continue
                    if parts[1] in members:
                        raise UserError("Duplicate package archive member")
                    if parts[1] == name + ".tar.Z":
                        payload = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
                        members[parts[1]] = payload
                        shutil.copyfileobj(tar.extractfile(member), payload)
                        payload.seek(0)
                    else:
                        if member.size > 64 * 1024 * 1024:
                            raise UserError("Package metadata is too large")
                        members[parts[1]] = tar.extractfile(member).read()
            if package is None:
                raise UserError("No native .pkg directory found in archive")
            return package[:-4], members
        except BaseException:
            for value in members.values():
                if hasattr(value, "close"):
                    value.close()
            raise


def check(path):
    name, members = read_members(path)
    try:
        return check_members(name, members)
    finally:
        for value in members.values():
            if hasattr(value, "close"):
                value.close()


def check_members(name, members):
    for ext in ("info", "sizes", "bom", "tar.Z"):
        if name + "." + ext not in members:
            raise UserError("Package is missing " + name + "." + ext)
    store = Store(members[name + ".bom"])
    top = store.directory(1)
    root = top["DefaultUnixBTree"][0]
    tables = store.directory(root)
    rows = store.tree(tables["Main"][0])
    inodes = {}
    pending = []
    for key, value in rows:
        parent = u32(key)
        inode = u32(value, 10)
        pending.append((parent, key[4:].decode(), inode, value))
    values = {}
    while pending:
        rest = []
        for parent, base, inode, value in pending:
            if parent == 1 and base == ".":
                target = "."
            elif parent in inodes:
                target = (inodes[parent] + "/" if inodes[parent] != "." else "") + base
            else:
                rest.append((parent, base, inode, value))
                continue
            safe_path(target)
            if inode in inodes and inodes[inode] != target:
                raise UserError("Duplicate BOM inode outside a hard-link group")
            if target in values:
                raise UserError("Duplicate BOM pathname")
            inodes[inode] = target
            values[target] = value
        if len(rest) == len(pending):
            raise UserError("BOM contains unresolved parent relationships")
        pending = rest
    links = {k.decode(): v for k, v in store.tree(tables["Links"][0])}
    for key, value in links.items():
        if value[0] == 0:
            seen = set()
            current = key
            while current not in seen:
                seen.add(current)
                record = links[current]
                if record[0]:
                    values[key.removeprefix("./")] = values[current.removeprefix("./")]
                    break
                current = record[1:].rstrip(b"\0").decode()
            else:
                raise UserError("BOM hard-link cycle has no leader")
    with tempfile.TemporaryFile() as payload:
        decompress(members[name + ".tar.Z"], payload)
        payload.seek(0)
        with tarfile.open(fileobj=payload, mode="r:") as tar:
            seen = set()
            for member in tar:
                target = member.name.removeprefix("./").rstrip("/") or "."
                safe_path(target)
                if target in seen:
                    raise UserError("Duplicate payload pathname: " + target)
                seen.add(target)
                value = values.get(target)
                if value is None:
                    raise UserError("Payload entry missing from BOM: " + target)
                mode, uid, gid = __import__("struct").unpack_from(">HHH", value)
                if (stat.S_IMODE(mode), uid, gid) != (
                    member.mode,
                    member.uid,
                    member.gid,
                ):
                    raise UserError("BOM/payload permissions differ: " + target)
                expected_type = stat.S_IFMT(mode)
                if member.isfile():
                    if expected_type != stat.S_IFREG or member.size != u32(value, 14):
                        raise UserError(
                            "BOM/payload file size or type differs: " + target
                        )
                    source = tar.extractfile(member)
                    # TarExtFile supports seeks needed by the checksum routine.
                    from .payload import checksum

                    if checksum(source, size=member.size) != u32(value, 18):
                        raise UserError("BOM/payload checksum differs: " + target)
                    if len(value) > 22:
                        import struct

                        count = u32(value, 22)
                        if len(value) != 26 + count * 16 or not 1 <= count <= 64:
                            raise UserError("Invalid architecture record: " + target)
                        source.seek(0)
                        header = source.read(28)
                        fat = header[:4] in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca")
                        if fat:
                            endian = ">" if header[:4] == b"\xca\xfe\xba\xbe" else "<"
                            if struct.unpack_from(endian + "I", header, 4)[0] != count:
                                raise UserError(
                                    "BOM/payload architecture count differs: " + target
                                )
                            source.seek(8)
                            table = source.read(count * 20)
                        else:
                            endian = "<" if header[:4] == b"\xce\xfa\xed\xfe" else ">"
                            if (
                                header[:4]
                                not in (b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xce")
                                or count != 1
                            ):
                                raise UserError(
                                    "BOM architecture record does not describe Mach-O: "
                                    + target
                                )
                        for index in range(count):
                            cpu, subtype, size, csum = struct.unpack_from(
                                ">iiII", value, 26 + 16 * index
                            )
                            if fat:
                                (
                                    actual_cpu,
                                    actual_subtype,
                                    offset,
                                    actual_size,
                                    align,
                                ) = struct.unpack_from(
                                    endian + "iiIII", table, index * 20
                                )
                            else:
                                actual_cpu, actual_subtype = struct.unpack_from(
                                    endian + "ii", header, 4
                                )
                                offset, actual_size = 0, member.size
                            if (
                                (cpu, subtype, size)
                                != (actual_cpu, actual_subtype, actual_size)
                                or offset + size > member.size
                                or checksum(source, offset, size) != csum
                            ):
                                raise UserError(
                                    "BOM/payload architecture record differs: " + target
                                )
                            source.seek(offset)
                            try:
                                check_image_mode(source.read(min(size, 28)), member.mode, target)
                            except ValueError as error:
                                raise UserError(str(error)) from error
                elif member.issym():
                    if (
                        expected_type != stat.S_IFLNK
                        or member.linkname.encode() + b"\0" != value[14:]
                    ):
                        raise UserError("BOM/payload symlink differs: " + target)
                elif member.isdir():
                    if expected_type != stat.S_IFDIR:
                        raise UserError("BOM/payload directory type differs: " + target)
                elif member.islnk():
                    if (
                        expected_type != stat.S_IFREG
                        or member.linkname.removeprefix("./") not in seen
                        or u32(values[member.linkname.removeprefix("./")], 10)
                        != u32(value, 10)
                    ):
                        raise UserError("Invalid hard link: " + target)
                else:
                    raise UserError("Unsupported payload entry: " + target)
            if seen != set(values):
                raise UserError("BOM contains files missing from the payload")
    info = {}
    for line in members[name + ".info"].decode().splitlines():
        fields = line.strip().split(None, 1)
        if not fields or fields[0].startswith("#"):
            continue
        info[fields[0]] = fields[1] if len(fields) > 1 else ""
    size_fields = {}
    for line in members[name + ".sizes"].decode().splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[1].isdigit():
            raise UserError("Invalid package .sizes metadata")
        size_fields[fields[0]] = int(fields[1])
    if (
        size_fields.get("NumFiles") != len(values)
        or size_fields.get("InstalledSize", 0) <= 0
        or size_fields.get("CompressedSize", 0) <= 0
    ):
        raise UserError("Package .sizes metadata does not match the payload")
    return {
        "name": name,
        "version": info.get("Version", ""),
        "entries": len(values),
        "info": info,
    }
