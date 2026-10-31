# nextpkg

Build native NEXTSTEP and OPENSTEP Installer packages on a modern host.
Python 3.11 or later is the only runtime requirement. No guest VM, root access,
NeXT SDK or external compression program is needed to create packages.

## Invoke nextpkg

In an extracted binary bundle, run `bin/nextpkg` from the bundle's root
directory. From a separate project directory, use its absolute path, such as
`/path/to/nextstep-toolchain/bin/nextpkg`. Alternatively, add the bundle's
absolute `bin` directory to PATH and invoke `nextpkg` directly:

```sh
export PATH="/path/to/nextstep-toolchain/bin:$PATH"
nextpkg --help
```

The examples below run from the bundle root and use `bin/nextpkg`. In a source
checkout, the equivalent command is `python3 src/nextpkg/nextpkg.py`.
The package builder itself does not need an SDK, even when the compiler used
to build your program does.

## Package a staging directory

Suppose you have already built an Intel NEXTSTEP executable at `build/example`
and want it installed as `/usr/local/bin/example`. Use a fresh staging
directory containing only files that belong in this package:

```sh
umask 022
mkdir -p stage/usr/local/bin
cp build/example stage/usr/local/bin/example
chmod 755 stage/usr/local/bin/example
bin/nextpkg init example.json --name Example --version 1.0 --root stage
```

Paths inside `stage/` become guest installation paths; `stage/` itself is not
installed. For example, `stage/usr/local/bin/example` becomes
`/usr/local/bin/example`. Do not put source trees, build directories or host
executables in the staging directory.

Open `example.json` in a text editor and set `title` and `description`. The
generated manifest includes a package revision and detects the payload
architectures.
Then build and validate the package:

```sh
bin/nextpkg build example.json --output dist
bin/nextpkg check dist/Example-1.0-1.pkg.I.tar.gz
```

The result is `Example-1.0-1.pkg.I.tar.gz` for this Intel executable, plus a
SHA256 sidecar. Fat executables produce the appropriate combination of N
(68k), I (Intel), H (HPPA) and S (SPARC); a four-target package uses `.NIHS`.
Packages with no architecture-specific files use `.pkg.tar.gz`. Use the
actual filename printed by `build` in subsequent commands.

The package directory inside is `Example.pkg`; Installer and the receipt show
version `1.0-1`. Increment `revision` when changing the package without changing
its upstream version. Existing archives are protected from replacement; use
`--force` for an intentional rebuild.

```sh
bin/nextpkg build example.json --dry-run
bin/nextpkg inspect dist/Example-1.0-1.pkg.I.tar.gz
```

`check` compares payload paths, permissions, numeric ownership, file checksums
and links with the BOM. It never installs the package or runs hooks. `inspect`
performs those checks and displays metadata; `--json` gives structured output.
A `.pkg` directory can be supplied instead of an archive. Checking is not a
substitute for testing the installed program on its target OS.

## Install in the guest

Extract the outer `.tar.gz` archive on the host or with a guest archive
utility. On the Linux host, for example:

```sh
mkdir unpacked
tar -xzf dist/Example-1.0-1.pkg.I.tar.gz -C unpacked
```

Transfer the complete `unpacked/Example.pkg` directory to the guest, preserving
its contents, then double-click it to open the native Installer. Run Installer
as root to install the files and native receipt. If you supplied a README, it
appears beside the package. Leave the `.bom`, `.info`, `.sizes`, `.tar.Z` and
any hooks inside `Example.pkg` intact. Do not extract the inner payload manually.

After installation, test the installed executable as an ordinary guest user.
A package does not automatically back up files it replaces; packages that
modify existing system files should implement a suitable `pre_install` hook.

## Explicit file mappings

A manifest can use `files` instead of `root`, or combine the two without
repeating installation paths. Source filenames are relative to the manifest.
Guest installation paths are relative to `location`, which defaults to `/`.

```json
{
  "name": "Example",
  "version": "1.0",
  "revision": 1,
  "title": "Example utility",
  "description": "A short description of what it does.",
  "architectures": "auto",
  "readme": "README.txt",
  "files": {
    "usr/local/bin/example": {"source": "build/example", "mode": "0755"},
    "bin/example": {"link": "/usr/local/bin/example"},
    "usr/bin/example": {"link": "/usr/local/bin/example"},
    "usr/local/share/example": {"directory": true, "mode": "0755"}
  }
}
```

Use strings such as `"0755"` for octal modes. JSON integers are also accepted
as numeric mode values, as in the older project manifests. Parent directories
are added automatically with mode 0755. A `hardlink` entry names another regular
file in the payload; its mode and ownership must match that file.

A staging directory preserves file modes and hard links, without following
symlinks. Ownership defaults to numeric root:wheel (0:0), regardless of who owns
files on the host. Use `uid` and `gid` globally or per explicit entry to override
that. Directories must be owner-readable, writable and searchable. Devices,
FIFOs and sockets are rejected. Explicit `source` mappings must name ordinary
files; use `link` for a symlink.

`architectures` defaults to `"auto"`. Explicit lists are useful for release
checks: every Mach-O executable must contain every advertised architecture.
Architecture detection and BOM records inspect the binary, not the filename.
Scripts are architecture independent. This tool does not compile programs or
make their runtime dependencies available.

A supplied README is included both beside the package in the archive and under
`usr/local/share/doc/NAME/README.txt`. A generated `BUILD.json` in that installed
directory records payload hashes and metadata without source paths. Source
code is included only if deliberately selected as payload.

## Hooks and dependencies

Optional `hooks` entries name executable programs or scripts on the host:

```json
"hooks": {
  "post_install": "package/post_install",
  "pre_delete": "package/pre_delete"
}
```

The supported names are `pre_install`, `post_install`, `pre_delete` and
`post_delete`. Mach-O hooks contribute to architecture detection and must
support every advertised target. Native Installer runs them with the package path as `$1` and
installation location as `$2`. They must return zero on success. The builder
never executes them on the host.

Setuid/setgid file modes are recorded in the tar archive and BOM. A generated
post-install hook restores them after native Installer's ownership changes.
When a custom hook must be combined with generated behavior, it must be a
Bourne-compatible shell script. Its body is embedded in a subprocess inside
the final hook so removal receipts do not depend on a missing helper file.
Dependency guards run before custom pre-install/pre-delete hooks; special-mode
restoration runs after a successful custom post-install hook.

`dependencies` lists runtime library basenames under `/usr/local/lib`.
`provides` lists libraries that this package supplies. These fields generate
checks and consumer declarations compatible with the project's library packages.
They apply to system library packages installed at `/`, not arbitrary relocatable
application bundles. Full dependency solving is outside this tool's scope.

`location` changes the default guest installation root; `relocatable` defaults
to false. An optional `icon` supplies the package TIFF. Installation always
requires authorization by default.

## Compatibility and limits

The builder writes the original NeXT binary BOM format, a USTAR payload with
UNIX `.Z` compression, native `.info`/`.sizes` files, and a deterministic outer
USTAR/gzip archive. Modes and owners are explicit. Directory space estimates
use fixed 1 KiB units rather than the host filesystem's allocation figures.

The initial format is single-volume, `LongFilenames NO`: payload paths are
limited to 97 bytes and link targets to 99 bytes. There is no bigtar, split-floppy,
remote-FTP or localized metadata generation. Files larger than the 32-bit BOM
size field are rejected. UTF-8 filenames retain their bytes; this does not add
Unicode display support to the guest.

BOM storage is bulk-loaded into balanced trees. The writer uses directly mapped
8 KiB blocks rather than emulating the native allocator's incremental packing.
Its uncompressed BOMs are larger but compress well in the distribution archive.
The reader handles the native packed allocation used by our reference packages
as well as generated direct blocks. It rejects unsupported shadowed stores and
externally stored record values rather than guessing their interpretation.

See [release validation](validation.md) for native checks and their limits.

## Development

From the toolchain source checkout:

```sh
python3 -m unittest discover -s src/nextpkg/tests -v
```

The tests use Python's standard library and an independent `gzip -dc` decoder
for compression interoperability. Host format tests do not require a VM.
Native compatibility tests and GUI lifecycle checks use disposable guests.

Dependency registrations are written under
`/usr/local/share/nextports/consumers`. Generated library removal checks read
both this directory and the historical `openstep-libs/consumers` directory,
so older installed consumers remain protected. Existing archives are unchanged
until rebuilt.

The `readme` field copies your supplied file unchanged. The same bytes appear
as `README.txt` beside the package and under
`/usr/local/share/doc/<package-name>/README.txt` in the installed payload.
Keep application descriptions and porting notes in your own packaging recipe.
