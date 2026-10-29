# Native child-wait investigation

NextStepCompat does not implement or export waitpid. Native process creation
is available, but native wait selectors and interruption differ from POSIX.

## Verified kernels

The optimized probes pass on NEXTSTEP 3.3 Intel, NeXT 68k, HPPA and SPARC and
Intel OPENSTEP. These are native-interface observations, not a POSIX
conformance pass.

- Native wait4 accepts positive child PIDs and returns the normal status word.
- Native setpgrp(0, getpid()) creates the child group used by the probes.
  Passing zero as the group ID is not the POSIX setpgid shorthand for its PID.
- Native selector zero means any child, rather than the caller's process group.
- Negative selectors, including -1, fail with ECHILD even with a matching live
  child. POSIX -1 must therefore be translated, not forwarded.
- With WNOHANG and no ready child, the kernel can overwrite the status argument.
  An adapter must use a private status word and copy it only on positive return.
- Both wait3 and wait4 return child status rather than EINTR despite observed
  signal delivery, with either setting of SA_RESTART. The sender sleeps between
  signal delivery and exit. These probes do not pinpoint when the kernel runs
  the handler relative to resuming the wait.

The existing POSIX signal regression separately completes 167 checks with zero
failures on the same OPENSTEP guest, including interrupted and restarted
reads. This distinguishes native wait behavior from a general signal-adapter
failure.

## Candidate and open requirements

The candidate is deliberately kept in tests/waitpid-candidate.c, outside the
component source glob. tests/build-wait-tests.py builds it explicitly, or uses
--probes-only for native observations. It is not installed in the canonical
compiler or a shared runtime.

The current candidate translates any-child waits, preserves untouched
statuses, rejects unknown option bits with EINVAL, and rejects process-group
selectors with ENOTSUP rather than selecting the wrong child. On OPENSTEP, its
explicit/ any-child, WNOHANG, stop/continue, null-status and signal-exit cases
pass. Its strict interruption regression fails because it inherits native
restart behavior.

Before promotion, settle and document the supported blocking/interruption
contract. Do not claim full POSIX semantics from these observations. Do not
steal other callers' children, install temporary process-wide signal handlers,
or silently implement process-group selection as an any-child wait. Preserve
the strict interruption probe as evidence if a native limitation remains.

Use the existing native libc wait4 entry instead of inventing an unverified
trap ABI. Its import is present in the original SDK; the missing waitpid
prototype implementation is a separate issue from that existing interface.
