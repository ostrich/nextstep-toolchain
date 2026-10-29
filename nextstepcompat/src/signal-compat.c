/* POSIX signal adapters. SPDX-License-Identifier: 0BSD */
#define _NEXT_SOURCE 1
#include <signal.h>
#include <syscall.h>
#include <errno.h>
#include <stddef.h>

extern int syscall(int, ...);
_Static_assert(sizeof(sigset_t) == sizeof(unsigned int), "native signal mask ABI");
_Static_assert(NSIG > 1 && NSIG <= 32, "native signal range");

static unsigned int valid_signals(void)
{
  /* NSIG includes the unused zero slot. Avoid signed shifts into bit 31. */
  return (~0U) >> (sizeof(unsigned int) * 8 - (NSIG - 1));
}

static int valid_signal(int signo)
{
  if (signo > 0 && signo < NSIG) return 1;
  errno = EINVAL;
  return 0;
}

int sigemptyset(sigset_t *set)
{
  if (!set) { errno = EFAULT; return -1; }
  *set = 0;
  return 0;
}

int sigfillset(sigset_t *set)
{
  if (!set) { errno = EFAULT; return -1; }
  *set = (sigset_t) valid_signals();
  return 0;
}

int sigaddset(sigset_t *set, int signo)
{
  if (!valid_signal(signo)) return -1;
  if (!set) { errno = EFAULT; return -1; }
  *set = (sigset_t) ((unsigned int) *set | (1U << (signo - 1)));
  return 0;
}

int sigdelset(sigset_t *set, int signo)
{
  if (!valid_signal(signo)) return -1;
  if (!set) { errno = EFAULT; return -1; }
  *set = (sigset_t) ((unsigned int) *set & ~(1U << (signo - 1)));
  return 0;
}

int sigismember(const sigset_t *set, int signo)
{
  if (!valid_signal(signo)) return -1;
  if (!set) { errno = EFAULT; return -1; }
  return (((unsigned int) *set >> (signo - 1)) & 1U) != 0;
}

int sigprocmask(int how, const sigset_t *set, sigset_t *oldset)
{
  int old;
  unsigned int mask;
  if (!set) {
    old = sigblock(0);
  } else {
    if (how != SIG_BLOCK && how != SIG_UNBLOCK && how != SIG_SETMASK) {
      errno = EINVAL;
      return -1;
    }
    mask = (unsigned int) *set & valid_signals();
    if (how == SIG_BLOCK) old = sigblock((int) mask);
    else if (how == SIG_SETMASK) old = sigsetmask((int) mask);
    else {
      /* Block handlers while doing the read/modify/write, so a handler's
         mask changes cannot be lost between the two kernel operations.
         Like native signals this is process-wide, not pthread_sigmask. */
      old = sigblock((int) valid_signals());
      if (oldset) *oldset = old;
      sigsetmask((int) ((unsigned int) old & ~mask));
      return 0;
    }
  }
  if (oldset) *oldset = old;
  return 0;
}

int sigpending(sigset_t *set)
{
  if (!set) { errno = EFAULT; return -1; }
  /* NEXTSTEP 3.3 adds this syscall; mk-108.1 predates it. */
  return syscall(SYS_sigpending, set);
}

int sigsuspend(const sigset_t *set)
{
  if (!set) { errno = EFAULT; return -1; }
  /* Kernel sigpause atomically installs the temporary mask, sleeps and
     restores the previous mask on signal return. Never emulate with pause. */
  return sigpause((int) ((unsigned int) *set & valid_signals()));
}

int sigaction(int signo, const struct sigaction *act, struct sigaction *oldact)
{
  struct sigvec vec, previous;
  int result;
  if (!valid_signal(signo) || signo == SIGKILL || signo == SIGSTOP) {
    errno = EINVAL;
    return -1;
  }
  if (act) {
    if (act->sa_flags & ~(SA_ONSTACK | SA_RESTART)) {
      /* In particular SA_NOCLDSTOP is declared by the SDK but unsupported
         by the BSD kernel interface. Do not silently claim to implement it. */
      errno = EINVAL;
      return -1;
    }
    vec.sv_handler = (void (*)(void)) act->sa_handler;
    vec.sv_mask = act->sa_mask;
    vec.sv_flags = (act->sa_flags & SA_ONSTACK ? SV_ONSTACK : 0) |
                  (act->sa_flags & SA_RESTART ? 0 : SV_INTERRUPT);
  }
  /* Call libc's sigvec, not the raw trap: libc owns the signal trampoline. */
  result = sigvec(signo, act ? &vec : NULL, oldact ? &previous : NULL);
  if (result == 0 && oldact) {
    oldact->sa_handler = (void (*)(int)) previous.sv_handler;
    oldact->sa_mask = previous.sv_mask;
    oldact->sa_flags = (previous.sv_flags & SV_ONSTACK ? SA_ONSTACK : 0) |
                      (previous.sv_flags & SV_INTERRUPT ? 0 : SA_RESTART);
  }
  return result;
}
