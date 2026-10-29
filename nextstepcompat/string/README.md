# Strings and byte comparisons

strstr uses the unchanged musl 1.2.6 implementation, including its empty-needle
handling, short-needle searches and two-way algorithm for longer needles.
sources.json pins the release and file hashes. COPYRIGHT retains its license.

The same release supplies memcmp, strcmp and strncmp. They compare bytes as
unsigned values, correcting native high-byte ordering failures. The public
header binds these replacements to namespaced symbols; original native
symbols remain available to existing binaries.

strdup, strndup, strnlen and strtok_r use pristine implementations from that
release. They fill missing APIs without changing the system library or SDK.
The build maps their malloc calls through a private adapter that sets ENOMEM
on failure; native NeXT malloc can leave errno unchanged. The pristine source
files are retained, and the mapping is recorded in the compiler commands.
