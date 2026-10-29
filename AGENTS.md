# Source ownership

This is the local source and release project for the NEXTSTEP cross-toolchain.
Do not create a GitHub remote or publish anything without explicit permission.

Keep compiler and cctools fixes in maintained patchsets, not generated trees.
Keep application ports in their own repositories or optional workspace folder.
Read docs/toolchain-workflow.md before changing compilers or runtimes. Never
update a qualified compiler snapshot in place. Use a fresh release output.

The binary bundle requires Python 3.11+ and supplies its other runtime tools.
SDK files, media, VM images and build products must remain ignored and must
never enter release archives. Do not commit or embed private filesystem paths.
Keep the public workflow limited to normal compiler and nextpkg commands.
