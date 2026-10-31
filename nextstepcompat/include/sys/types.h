/* Select POSIX types before the SDK's one-shot type guard is evaluated.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SYS_TYPES_H
#define NEXTSTEPCOMPAT_SYS_TYPES_H
#include <standards.h>
#include_next <sys/types.h>
#include <ns33-fdset.h>
#endif
