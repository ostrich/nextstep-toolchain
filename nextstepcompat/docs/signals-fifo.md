# Signal and FIFO adapters

The library exports ordinary standard symbols, so configure link probes can
find them without private function names or injected feature answers. Original
SDK types and the sigaction structure layout are preserved.

## Signals

- sigemptyset, sigfillset, sigaddset, sigdelset and sigismember use the native
  32-bit mask, with valid signal numbers 1 through NSIG-1. Invalid numbers
  return -1 and EINVAL without changing the set.
- sigprocmask maps BLOCK and SETMASK directly to BSD calls. UNBLOCK blocks
  catchable signals while reading and updating the old mask. Aliased input
  and output sets are supported. A null input queries the mask regardless
  of the how argument. The kernel excludes SIGKILL and SIGSTOP.
- sigpending invokes the NEXTSTEP 3.3 kernel's SYS_sigpending. This syscall
  does not exist in the older mk-108.1 source snapshot. No pending-signal
  state is inferred from handlers or fabricated in userspace.
- sigsuspend uses native sigpause for atomic mask replacement and sleep;
  the kernel restores the old mask after handler return.
- sigaction uses libc sigvec so that libc retains control of its native
  trampoline. SA_ONSTACK maps to SV_ONSTACK. SA_RESTART is the inverse of
  SV_INTERRUPT; zero flags request interrupted rather than restarted calls.
  Old handler, mask and flags can be queried and input/output can alias.

SA_NOCLDSTOP is declared in the SDK but the BSD interface does not implement
it. Requests containing it or other unsupported flags fail with EINVAL and
leave the previous disposition unchanged. No SA_SIGINFO, SA_NODEFER,
SA_RESETHAND, SA_NOCLDWAIT, realtime signals or pthread_sigmask is provided.
Other native restrictions on signal dispositions remain in force.

Masks are process-wide, as in the underlying BSD API. Concurrent mask changes
from different native threads are not made into POSIX per-thread operations.
Do not substitute these functions for a pthread signal implementation.

## FIFOs

mkfifo passes the requested permission/special bits and S_IFIFO to mknod.
The kernel applies umask and directory permissions, creates the FIFO inode
and supplies all read/write, open, select and signal semantics. Syscall error
returns are preserved. No custom filesystem object or emulation is created.

The additional signal.h and sys/stat.h wrappers must precede the derived
SDK overlay. The maintained compiler driver enforces this order, including
when --compat-headers supplies an independent component build.

## Validation scope

The target tests are tests/signals.c and tests/fifo.c. They run in disposable
guests, drop to an ordinary account and report their own assertion counts.
The signal test exercises set operations, pending delivery, handler masks,
mask restoration after sigsuspend, flags and interrupted/restarted pipe reads.
The FIFO test exercises permissions, nonblocking operations, byte transfer,
select, EOF and EPIPE. Neither is an exhaustive POSIX conformance suite.
Compiler integration records and actual target results are maintained in the
compiler repository, separately from this component's interface contract.
