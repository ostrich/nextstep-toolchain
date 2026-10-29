# Included components

The new distribution helpers, nextpkg and nextufs use their included MIT
licenses. This does not relicense GCC, cctools or their dependencies.

GCC and its patches use GPLv3; runtime components additionally carry the GCC
Runtime Library Exception. GNU libc and its loaders use LGPLv2.1 or later;
GMP, MPFR and MPC use their upstream LGPL terms. ISL uses MIT and Zstandard
uses its included dual license. The applicable GPL/LGPL texts and runtime
exception are included here. Cctools and mkshlib retain the licenses in their
pinned upstream sources; see the source manifests and component directories.

share/host-runtime.json records the actual bundled host-library filenames and
hashes. Release source materials must correspond to those binary inputs, not
merely the latest available source. Before public upload, collect the matching
upstream source archives and any distributor patches alongside the source
repository. No proprietary SDK material belongs in those source materials.
