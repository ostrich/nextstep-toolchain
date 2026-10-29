# Native effective credential declarations

The original NEXTSTEP SDK exports seteuid and setegid in libsys_s and declares
them in bsd/libc.h, but omits their declarations from unistd.h. NextStepCompat
now exposes those same uid_t/gid_t prototypes through its unistd.h wrapper.
No replacement implementation or shared export is introduced.

A rebuild and staged install changed only include/nextstepcompat/unistd.h.
All compiler and library binary hashes, including static NextStepCompat, stayed
identical. NIHS C and C++ links passed, as did the 16 header-order checks.
The child-only Intel OPENSTEP runtime probe passed native no-op calls, dropping
effective UID/GID, denying unauthorized changes, restoring the original IDs
and confirming the parent retained root credentials. NIHS credential runtime
checks remain to be included in the broader upstream guest batch.
