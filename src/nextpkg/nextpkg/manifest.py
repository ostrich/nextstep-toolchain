"""Validate user manifests and prepare deterministic installation payloads."""

import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from .payload import Entry, scan_file


class UserError(ValueError):
    pass


def mode_number(value, label):
    try:
        result = int(value, 8) if isinstance(value, str) else value
        if type(result) is not int or not 0 <= result <= 0o7777:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise UserError(f'{label}: use an octal mode such as "0755"') from None


def safe_path(path):
    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or any(c in path for c in "\0\n\r\t")
    ):
        raise UserError(
            f"Invalid payload path: {path!r}; use a relative installation path"
        )
    parts = path.split("/")
    if any(p in ("", "..") for p in parts) or any(
        p == "." for p in parts if len(parts) > 1
    ):
        raise UserError(f"Invalid payload path: {path!r}")
    path = str(PurePosixPath(path))
    if len(("./" + path).encode()) > 99:
        raise UserError(
            f"{path}: exceeds the native short-path limit (97 bytes); shorten the installation path"
        )
    return path


def load(path):
    path = path.resolve()
    try:

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise UserError("Duplicate manifest key: " + key)
                result[key] = value
            return result

        spec = json.loads(path.read_text(), object_pairs_hook=unique_object)
    except json.JSONDecodeError as error:
        raise UserError(
            f"{path.name}:{error.lineno}:{error.colno}: {error.msg}"
        ) from None
    if not isinstance(spec, dict):
        raise UserError("The manifest must be a JSON object")
    allowed = {
        "name",
        "version",
        "revision",
        "title",
        "description",
        "root",
        "files",
        "readme",
        "hooks",
        "icon",
        "architectures",
        "location",
        "relocatable",
        "uid",
        "gid",
        "dependencies",
        "provides",
    }
    unknown = set(spec) - allowed
    if unknown:
        raise UserError("Unknown manifest field(s): " + ", ".join(sorted(unknown)))
    name = spec.get("name")
    if (
        not isinstance(name, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", name)
        or len(name) > 60
    ):
        raise UserError(
            "name: use a package identifier of at most 60 letters, digits, dots, underscores, + or -"
        )
    version = spec.get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._+-]*", version
    ):
        raise UserError('version: enter an upstream version such as "1.2.3"')
    revision = spec.get("revision", 1)
    if type(revision) is not int or revision < 1:
        raise UserError("revision: enter a positive integer")
    for field in ("title", "description"):
        value = spec.get(field, name if field == "title" else "")
        if (
            not isinstance(value, str)
            or any(c in value for c in "\0\n\r")
            or len(value.encode()) > 1023
        ):
            raise UserError(f"{field}: use a single line of at most 1023 bytes")
        spec[field] = value
    for field in ("uid", "gid"):
        if type(spec.get(field, 0)) is not int or not 0 <= spec.get(field, 0) <= 65535:
            raise UserError(f"{field}: must be a numeric owner in the range 0..65535")
    location = spec.get("location", "/")
    if (
        not isinstance(location, str)
        or not location.startswith("/")
        or any(c in location for c in "\0\n\r\t")
        or ".." in PurePosixPath(location).parts
    ):
        raise UserError("location: use an absolute guest installation directory")
    if type(spec.get("relocatable", False)) is not bool:
        raise UserError("relocatable: must be true or false")
    spec["location"] = location
    entries = {}

    def add(target, entry):
        target = safe_path(target)
        if target in entries:
            raise UserError(f"{target}: duplicate payload entry")
        entries[target] = entry

    if "root" in spec:
        if not isinstance(spec["root"], str):
            raise UserError("root: use a path to a staging directory")
        root = (path.parent / spec["root"]).resolve()
        if not root.is_dir():
            raise UserError(f'Payload root does not exist: {spec["root"]}')
        inodes = {}

        def walk(directory):
            for source in sorted(directory.iterdir()):
                target = source.relative_to(root).as_posix()
                st = source.lstat()
                mode = stat.S_IMODE(st.st_mode)
                opts = dict(uid=spec.get("uid", 0), gid=spec.get("gid", 0))
                if source.is_symlink():
                    entry = Entry(
                        target, "symlink", 0o777, target=os.readlink(source), **opts
                    )
                elif stat.S_ISDIR(st.st_mode):
                    entry = Entry(target, "directory", mode, **opts)
                elif stat.S_ISREG(st.st_mode):
                    identity = st.st_dev, st.st_ino
                    if identity in inodes:
                        entry = Entry(
                            target, "hardlink", mode, target=inodes[identity], **opts
                        )
                    else:
                        inodes[identity] = target
                        entry = Entry(target, "file", mode, source=source, **opts)
                else:
                    raise UserError(
                        f"{target}: device nodes, sockets and FIFOs are not supported as package payloads"
                    )
                add(target, entry)
                if entry.kind == "directory":
                    walk(source)

        walk(root)
    files = spec.get("files", {})
    if not isinstance(files, dict):
        raise UserError("files: use an object mapping installation paths to entries")
    for target, value in files.items():
        target = safe_path(target)
        if not isinstance(value, dict):
            raise UserError(f"{target}: expected an entry object")
        if set(value) - {
            "source",
            "mode",
            "link",
            "hardlink",
            "directory",
            "uid",
            "gid",
        }:
            raise UserError(f"{target}: unknown entry field")
        kinds = [
            kind
            for kind in ("source", "link", "hardlink", "directory")
            if kind in value
        ]
        if len(kinds) != 1:
            raise UserError(
                f"{target}: specify exactly one of source, link, hardlink or directory"
            )
        kind = kinds[0]
        default_mode = (
            0o755 if kind == "directory" else 0o777 if kind == "link" else 0o644
        )
        opts = dict(
            mode=mode_number(value.get("mode", default_mode), target),
            uid=value.get("uid", spec.get("uid", 0)),
            gid=value.get("gid", spec.get("gid", 0)),
        )
        if any(
            type(opts[k]) is not int or not 0 <= opts[k] <= 65535
            for k in ("uid", "gid")
        ):
            raise UserError(f"{target}: uid/gid must be numeric values in 0..65535")
        if kind == "source":
            if not isinstance(value[kind], str):
                raise UserError(f"{target}: source must be a filename")
            source = path.parent / value[kind]
            if source.is_symlink() or not source.is_file():
                raise UserError(
                    f"{target}: source must be an ordinary file, not a symlink"
                )
            entry = Entry(target, "file", source=source.resolve(), **opts)
        elif kind == "directory":
            if value[kind] is not True:
                raise UserError(f"{target}: directory must be true")
            entry = Entry(target, "directory", **opts)
        else:
            link = value[kind]
            if (
                not isinstance(link, str)
                or not link
                or any(c in link for c in "\0\n\r\t")
                or len(link.encode()) > 99
            ):
                raise UserError(f"{target}: invalid or overlong link target")
            entry = Entry(
                target, "symlink" if kind == "link" else "hardlink", target=link, **opts
            )
        add(target, entry)
    if not entries:
        raise UserError("No payload files: provide root or files in the manifest")
    for target in list(entries):
        for parent in PurePosixPath(target).parents:
            parent = str(parent)
            if parent not in entries:
                entries[parent] = Entry(
                    parent,
                    "directory",
                    0o755,
                    uid=spec.get("uid", 0),
                    gid=spec.get("gid", 0),
                )
            elif entries[parent].kind != "directory":
                raise UserError(f"{target}: parent {parent} is not a directory")
    for entry in entries.values():
        if entry.path == "." and entry.kind != "directory":
            raise UserError("The payload root must be a directory")
        if entry.kind == "directory" and entry.mode & 0o700 != 0o700:
            raise UserError(
                f"{entry.path}: package directories must be owner-readable, writable and searchable"
            )
        if entry.kind == "hardlink":
            target = entries.get(entry.target)
            if target is None or target.kind != "file":
                raise UserError(
                    f"{entry.path}: hardlink must name a regular payload file"
                )
            declared = files.get(entry.path, {})
            for field in ("mode", "uid", "gid"):
                if field not in declared:
                    setattr(entry, field, getattr(target, field))
            if (entry.mode, entry.uid, entry.gid) != (
                target.mode,
                target.uid,
                target.gid,
            ):
                raise UserError(
                    f"{entry.path}: hardlink metadata differs from its target"
                )
        if entry.kind == "symlink" and len(entry.target.encode()) > 99:
            raise UserError(f"{entry.path}: symlink target exceeds the native limit")
    # Auxiliaries are host inputs only, never guest installation paths.
    for field in ("readme", "icon"):
        if field in spec:
            if (
                not isinstance(spec[field], str)
                or not (path.parent / spec[field]).is_file()
            ):
                raise UserError(f"{field}: file does not exist")
            spec[field] = path.parent / spec[field]
    hooks = spec.get("hooks", {})
    if not isinstance(hooks, dict) or set(hooks) - {
        "pre_install",
        "post_install",
        "pre_delete",
        "post_delete",
    }:
        raise UserError(
            "hooks: supported names are pre_install, post_install, pre_delete and post_delete"
        )
    spec["hooks"] = {}
    for role, source in hooks.items():
        if not isinstance(source, str) or not (path.parent / source).is_file():
            raise UserError(f"hooks.{role}: file does not exist")
        spec["hooks"][role] = path.parent / source
    for field in ("dependencies", "provides"):
        values = spec.get(field, [])
        if not isinstance(values, list) or any(
            not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9._+-]+", v)
            for v in values
        ):
            raise UserError(f"{field}: use a list of library basenames")
        spec[field] = values
    if (spec["dependencies"] or spec["provides"]) and (
        spec["location"] != "/" or spec.get("relocatable", False)
    ):
        raise UserError(
            "Library dependency declarations require a non-relocatable system package at /"
        )
    archs = spec.get("architectures", "auto")
    if archs != "auto" and (
        not isinstance(archs, list)
        or not archs
        or any(not isinstance(arch, str) for arch in archs)
        or len(archs) != len(set(archs))
        or set(archs) - {"i386", "m68k", "hppa", "sparc"}
    ):
        raise UserError(
            'architectures: use "auto" or a list containing i386, m68k, hppa and/or sparc'
        )
    spec["revision"] = revision
    return spec, sorted(entries.values(), key=lambda e: e.path)
