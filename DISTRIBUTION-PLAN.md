# Distribution scope

The deliverable is a relocatable Linux x86-64 toolchain, with build scripts,
maintained patchsets, runtime support, nextpkg and SDK extraction tools.
It requires Python 3.11+ and host 32-bit x86 execution support. SDK files,
media, application ports, guest images and working directories are excluded.

The root README describes setup and source builds. PORTING.md describes normal
application workflows. docs/validation.md records release checks and limits.
The archive includes its own usage, packaging and shared-library instructions,
component notices and integrity manifests.

Build and archive creation are local operations. Publication is separate from
building; no build script creates a remote repository or uploads a release.
