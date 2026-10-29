/* POSIX signal interfaces over the native process-wide BSD signal model.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SIGNAL_H
#define NEXTSTEPCOMPAT_SIGNAL_H
#include <standards.h>
#include_next <signal.h>
/* Match the handler signature used by the POSIX signal declarations. */
#undef SIG_ERR
#define SIG_ERR ((void (*)(int))-1)
/* Keep the native sigaction layout and existing SA_NOCLDSTOP value. */
#ifndef SA_ONSTACK
#define SA_ONSTACK 0x0001
#endif
#ifndef SA_RESTART
#define SA_RESTART 0x0002
#endif
#endif
