/* Additional ISO/POSIX errors used by the modern runtime.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_ERRNO_H
#define NEXTSTEPCOMPAT_ERRNO_H
#include_next <errno.h>
/* The original SDK hides this existing kernel error without _POSIX_SOURCE. */
#ifndef ENOSYS
#define ENOSYS 87
#endif
/* Keep runtime-only errors outside the original kernel's error range.
   Do not alias them to EINVAL or EAGAIN: std::errc must distinguish them. */
#ifndef EILSEQ
#define EILSEQ 4096
#endif
#ifndef ENOMSG
#define ENOMSG 4097
#endif
#ifndef EOVERFLOW
#define EOVERFLOW 4098
#endif
#ifndef EOWNERDEAD
#define EOWNERDEAD 4099
#endif
#ifndef ENOTRECOVERABLE
#define ENOTRECOVERABLE 4100
#endif
#ifndef ENOTSUP
#define ENOTSUP EOPNOTSUPP
#endif
#endif
