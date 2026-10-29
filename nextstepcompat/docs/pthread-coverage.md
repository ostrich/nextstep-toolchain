# Pthread API coverage

This matrix describes the implementation contract, not POSIX certification.
See [design, native research and limits](pthreads.md) and
[qualification](pthread-validation.md). The machine-readable source is
[pthread-coverage.json](pthread-coverage.json).

| API | Status | Contract |
| --- | --- | --- |
| `pthread_self` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_equal` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_create` | partial | Native default unlimited worker pool; native allocator exhaustion is not fully recoverable. |
| `pthread_join` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_detach` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_exit` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_key_create` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_key_delete` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_getspecific` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_setspecific` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_once` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cancel` | partial | Supported pthread cancellation points only; native libc blocking calls are not interposed. |
| `pthread_testcancel` | partial | Managed Cthreads only. |
| `pthread_setcancelstate` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_setcanceltype` | partial | Deferred only; asynchronous type returns ENOTSUP. |
| `pthread_getschedparam` | partial | Queries qualified Mach timeshare policy; reports POSIX priority zero. |
| `pthread_setschedparam` | partial | SCHED_OTHER, priority zero only. |
| `pthread_setschedprio` | partial | Priority zero only. |
| `pthread_getconcurrency` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_setconcurrency` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_kill` | partial | Signal zero only, for live registered threads. |
| `pthread_sigmask` | rejected | Native masks are process-wide; per-thread masking is unavailable. |
| `pthread_atfork` | partial | Used by new code compiled against the canonical fork overlay; old native imports cannot be retrofitted. |
| `pthread_attr_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_condattr_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_condattr_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlockattr_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlockattr_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_barrierattr_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_barrierattr_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_getdetachstate` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_setdetachstate` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_getinheritsched` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_setinheritsched` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_getscope` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_setscope` | partial | PTHREAD_SCOPE_SYSTEM only; native worker limit must stay unlimited. |
| `pthread_attr_getschedpolicy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_setschedpolicy` | partial | SCHED_OTHER only; FIFO/RR return ENOTSUP. |
| `pthread_attr_getschedparam` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_setschedparam` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_attr_getstacksize` | rejected | Usable default size is not guessed from the allocation mask. |
| `pthread_attr_setstacksize` | rejected | No qualified per-thread native-compatible stack allocator. |
| `pthread_attr_getguardsize` | rejected | Native guard geometry is not a portable per-thread attribute. |
| `pthread_attr_setguardsize` | rejected | No qualified per-thread native-compatible guard allocator. |
| `pthread_mutexattr_gettype` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_settype` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_getpshared` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_setpshared` | partial | Process-private only; shared returns ENOTSUP. |
| `pthread_mutexattr_getprotocol` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_setprotocol` | partial | PTHREAD_PRIO_NONE only. |
| `pthread_mutexattr_getrobust` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutexattr_setrobust` | partial | Managed-thread, process-private robust ownership only. |
| `pthread_mutexattr_getprioceiling` | rejected | Priority-protection protocol is unavailable. |
| `pthread_mutexattr_setprioceiling` | rejected | Priority-protection protocol is unavailable. |
| `pthread_condattr_getpshared` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_condattr_setpshared` | partial | Process-private only; shared returns ENOTSUP. |
| `pthread_condattr_getclock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_condattr_setclock` | partial | CLOCK_REALTIME only. |
| `pthread_rwlockattr_getpshared` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlockattr_setpshared` | partial | Process-private only; shared returns ENOTSUP. |
| `pthread_barrierattr_getpshared` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_barrierattr_setpshared` | partial | Process-private only; shared returns ENOTSUP. |
| `pthread_attr_getstack` | rejected | Native aligned Cproc stacks have no qualified per-thread allocator. |
| `pthread_attr_setstack` | rejected | Native aligned Cproc stacks have no qualified per-thread allocator. |
| `pthread_mutex_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cond_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cond_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_lock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_trylock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_unlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_consistent` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_mutex_timedlock` | partial | Absolute realtime deadlines; Mach millisecond resolution and bounded clock-adjustment rechecks. |
| `pthread_mutex_getprioceiling` | rejected | Priority-protection protocol is unavailable. |
| `pthread_mutex_setprioceiling` | rejected | Priority-protection protocol is unavailable. |
| `pthread_cond_signal` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cond_broadcast` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cond_wait` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cond_timedwait` | partial | Absolute realtime deadlines; Mach millisecond resolution and bounded clock-adjustment rechecks. |
| `pthread_rwlock_rdlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_wrlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_tryrdlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_trywrlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_unlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_rwlock_timedrdlock` | partial | Absolute realtime deadlines; Mach millisecond resolution and bounded clock-adjustment rechecks. |
| `pthread_rwlock_timedwrlock` | partial | Absolute realtime deadlines; Mach millisecond resolution and bounded clock-adjustment rechecks. |
| `pthread_barrier_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_barrier_wait` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_barrier_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_spin_init` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_spin_lock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_spin_trylock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_spin_unlock` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_spin_destroy` | implemented | See family contract in pthreads.md; not a full POSIX certification. |
| `pthread_cleanup_push` | partial | Managed exit/cancellation only; C++ forced unwinding is unavailable. |
| `pthread_cleanup_pop` | partial | Paired lexical scope; C++ forced unwinding is unavailable. |
| `pthread_getcpuclockid` | not-provided | No qualified per-thread clock-ID and clock_gettime ABI. |
| `pthread_cond_clockwait` | not-provided | Only realtime waits are currently implemented. |
| `pthread_mutex_clocklock` | not-provided | Only realtime waits are currently implemented. |
| `pthread_rwlock_clockrdlock` | not-provided | Only realtime waits are currently implemented. |
| `pthread_rwlock_clockwrlock` | not-provided | Only realtime waits are currently implemented. |
| `sem_*` | not-provided | An async-signal-safe sem_post needs a different counter/IPC design. |
| `pthread_attr_getstackaddr / pthread_attr_setstackaddr` | not-provided | Obsolete stack-address interfaces; custom stacks are not supported. |
