# POSIX threads on NEXTSTEP

NextStepCompat implements process-private pthread operations using native
Cthreads for execution and Mach message ports for blocking and wakeups. This
is a documented compatibility implementation, not a claim that the underlying
system is POSIX-threads conforming. Read the limits below before selecting it
for software which depends on cancellation, signals, real-time scheduling or
custom stacks.

The maintained target is NEXTSTEP 3.3 on Intel, NeXT 68k, HPPA and SPARC, plus
Intel OPENSTEP 4.2. The NeXT 1.x sources explain the original design; they are
not evidence that later kernels or libraries have identical behavior. NEXTSTEP
1.x/2.x execution is not qualified; the current SDK and runtime requirement
remains NEXTSTEP 3.3 or OPENSTEP 4.2.

## Initial audit

The previous implementation provided native-sized mutexes and conditions,
thread identity, a mutex-protected once function, default joinable creation,
join/exit, and 128 generation-tagged keys with destructor iterations. It had
no detach, cancellation, cleanup stack, timed waits, mutex types, rwlocks,
barriers, spinlock API or initialized attributes. Every non-null attribute
pointer was rejected.

Important semantic gaps included a once initializer leaving its mutex locked
on thread exit, lack of detached-record reclamation, no cancellation protocol
for a joining thread, and no compatibility-registry repair around native fork.
The native condition queue could not simply be given a timeout: removing its
private Cproc waiter from outside the library would race its scheduler.

## Execution, identity and lifetime

`pthread_t` remains `cthread_t`. All public object sizes and static initializers
from the earlier ABI remain valid. A separate registry owns each managed
thread's keys, cleanup stack, cancellation state and join/detach claim.
Native Cthreads' application data slot is never used. A managed thread's
termination invalidates its outstanding stalled mutex/rwlock ownership,
without releasing those locks, so a recycled Cthread handle cannot inherit
recursive ownership. Handles expire after
join or detached termination; reusing such a handle is outside POSIX's valid
lifetime and can refer to a later recycled Cthread.

Creation publishes the registry record before releasing its trampoline.
Exactly one successful join claim or detach consumes the native joinable
resource. A cancelled joiner releases its claim without detaching the target.
Native join and removal of the registry entry are serialized to prevent a
recycled native handle from racing the old entry's removal. Detached records
are removed on completion; completed joinable records remain until consumed.
Initial-thread pthread_exit waits for remaining native Cthreads and gives the
process a zero exit status. Returning from main still terminates the process.

The initial thread and pthread-created threads have an owned exit boundary.
Foreign Cthreads may use the mutex, condition, once, rwlock and barrier APIs,
but cannot acquire TLS associations or robust mutex ownership. Native
cthread_exit from a managed thread bypasses cleanup and is unsupported. Using
native synchronization functions on a pthread mutex/condition is unsupported;
the preserved native-sized layout is an ABI promise, not shared ownership of
the native scheduler's queues.

The native worker limit must remain unlimited. Creation rejects a nonzero
cthread_limit with ENOTSUP rather than risk queuing a worker behind a thread
which needs that worker to make progress. Native Cthreads and the compiler's separate C++ gthread runtime are not replaced.
In particular, this change does not rewrite every native library lock site.
Native cthread_fork has allocation
paths without reliable error recovery. Adapter-owned allocation failures are
reported, but it cannot make arbitrary native allocator exhaustion safe.

## Synchronization protocol

A native gate protects registries and private synchronizer state. Compiler
barriers and architecture-specific release fences preserve publication on
Intel, 68k, SPARC and HPPA. The gate is never held while user callbacks run or
while receiving a Mach wakeup. SPARC native spin_lock has a contended-path
register defect; acquisition uses the verified nonblocking native atomic
primitive instead, including the initialization gate. Blocking calls allocate a private receive port,
enqueue before releasing ownership, and receive a durable message. Notification
cannot disappear between unlocking and sleeping.

Queue transitions, timeout decisions and cancellation requests are serialized.
A signaled waiter remains alive until its port is no longer accessible to a
sender. A cancelled condition waiter transfers a consumed notification to
another eligible waiter, reacquires its original mutex, then invokes cleanup.
The condition's dynamic mutex binding applies to its blocked queue, not to
threads which have already been signaled and are reacquiring their mutexes.
A waiting thread pins the mutex against destruction while ownership is released.

Timed waits use absolute CLOCK_REALTIME deadlines, round up the Mach
millisecond timeout, and recheck wall time at least once a second. Spurious
or interrupted Mach receives do not become EINTR. Clock adjustments are
observed on the bounded recheck, not through kernel absolute-timer notification;
large wall-clock jumps can therefore take up to one second to affect a wait. A free timed mutex/rwlock
can be acquired even with an expired deadline. No monotonic-clock attribute
is silently treated as realtime.

Recursive mutexes release one recursion level during a condition wait. Waiting
with depth greater than one can therefore prevent another thread from acquiring
the mutex, as described by POSIX. Error-checking mutexes diagnose wrong-owner
unlock and recursive lock attempts. Trylock returns EBUSY for an already owned
non-recursive mutex.

Rwlocks track reader recursion per owner, admit existing recursive readers
while a writer waits, and prevent new readers from indefinitely bypassing queued
writers. Upgrades and writer recursion return EDEADLK rather than pretend to
succeed. They do not promise real-time priority ordering. Barriers are reusable,
with a separate notification for each generation and one serial-thread return.
Spinlocks use the native atomic lock primitive and explicit memory fences.

## Robust mutexes

Process-private robust mutexes are supported for managed threads. On exit,
after cleanup handlers and TLS destructors, the registry releases owned robust
mutexes and marks them inconsistent. The next owner receives EOWNERDEAD while
holding the mutex. pthread_mutex_consistent repairs it. Unlocking without repair
marks it permanently ENOTRECOVERABLE and wakes all blocked lockers. Owner death
during a repair attempt produces EOWNERDEAD again. Condition reacquisition can
return the robust error while preserving the appropriate ownership state.

This does not detect arbitrary native thread_terminate or cthread_exit calls
which bypass the managed exit path. Robust acquisition by a foreign Cthread
returns ENOTSUP. Process-shared robustness needs kernel-supported owner-death
notification or a different shared-memory identity/ownership protocol.

## Cancellation, cleanup and TLS

Deferred cancellation is implemented at pthread_testcancel, pthread_join,
pthread_cond_wait and pthread_cond_timedwait. Disabled requests remain pending.
Changing back to ENABLE does not itself become a deferred cancellation point.
Mutex, rwlock, spinlock and barrier operations are not cancellation points.
Cancellation runs lexical cleanup handlers in reverse order before TLS
destructors. Destructors clear values before callbacks, can repopulate keys,
and run for at most PTHREAD_DESTRUCTOR_ITERATIONS rounds. Key generations do
not wrap and deleted keys never revive a previous association.

Native read, write, select, wait and other libc calls have not been turned into
pthread cancellation points. Therefore this is not complete POSIX deferred
cancellation. A request cannot interrupt a worker blocked indefinitely inside
an unwrapped native syscall. Applications must use the implemented points or
explicit pthread_testcancel at safe boundaries.

Asynchronous cancellation returns ENOTSUP and leaves the old type untouched.
Mach thread_abort only interrupts some kernel waits; it does not unwind user
cleanup frames or terminate the Cthread correctly. thread_terminate bypasses
allocator, Cthread and adapter ownership. A correct future implementation needs
per-architecture context trampolines, protected internal critical sections and
an audited syscall/allocator boundary. It must not destroy a kernel thread as
an approximation to pthread cancellation.

Cleanup macros have paired lexical scope. Do not throw C++ exceptions through once initializers, cleanup handlers or
TLS destructors. C++ exception unwinding through these C macros is not
implemented; cleanup is provided for pthread_exit and
supported cancellation. Longjmp across an active cleanup frame is unsupported.

## Attributes and scheduling

Initialized create attributes support joinable/detached state and inherited
or explicit SCHED_OTHER/priority zero scheduling. Creation waits for native
startup, captures the worker's actual kernel identity, and verifies/restores
Mach timeshare policy before invoking user code. An unsupported caller policy
is rejected rather than falsely inherited. Startup failure never runs the
user function or publishes a successful handle. A fast detached worker's
record stays pinned until creation has finished publishing it.

Scheduling queries use Mach THREAD_SCHED_INFO while the record is protected
against native-worker recycling. The supported POSIX priority is zero; native
dynamic priority values are implementation details, not POSIX fixed priorities.
SCHED_OTHER can be set or restored through thread_policy. FIFO/RR remain
unsupported: historical fixed-priority support is conditional in the kernel,
and policy/privilege/quantum behavior cannot be inferred from the header names.
The concurrency setting is a POSIX hint, not a call to the potentially
deadlocking native worker limit.

Custom stack addresses, stack sizes and guards return ENOTSUP. Cthread identity
and its private Cproc/MIG state rely on the native aligned stack allocation.
Changing the Mach start PC/SP alone does not construct that environment.
A future native-compatible stack allocator and per-architecture startup code
could supply this feature. The implementation does not invent default usable
stack/guard sizes from the allocation mask.

Only PTHREAD_PROCESS_PRIVATE, PTHREAD_PRIO_NONE and CLOCK_REALTIME are accepted.
Priority inheritance/protection, ceiling operations and process-shared objects
return explicit errors. Private heap pointers and task-local Mach port names
cannot be placed into shared memory and advertised as inter-process locks.

## Signals, errno and fork

Native BSD masks are process-wide. pthread_sigmask returns ENOTSUP without
changing any mask. pthread_kill accepts signal zero for a live registered
thread, but rejects actual directed signals. Native process signals remain
available through signal/sigaction; the adapter does not install a private
cancellation signal or steal an application's signal number.

Pthread calls return their error numbers directly. Native errno remains a
legacy interface; Cthreads also supplies cthread_errno for the current Cproc's
last native syscall error. This work does not interpose every libc entry to
create a modern errno lvalue ABI. Callers must not mistake global errno for
an independent thread-local value.

The canonical unistd overlay binds newly compiled fork calls to ns33_fork.
That wrapper invokes prepare handlers in reverse registration order, native
fork, and parent/child handlers in registration order. Native libc retains
responsibility for its Mach, malloc and Cthreads fork hooks. Handler-list boundaries are
snapshotted without allocation before callbacks, which execute without the
adapter gate. A handler registered by a callback applies to the next fork.

The child retains only the calling thread's TLS/cleanup record. Vanished
threads' destructors are not run in the child. Wait queues discard pointers
to vanished stacks. An in-progress once entry owned by a vanished thread is discarded so
it can be retried. Initializer records live in transient heap storage: native
fork can unmap the vanished threads' stacks before our child hook runs.
Completion and cancellation free these records; completed once objects retain
no sidecar allocation. Ordinary application mutexes owned by vanished threads are
not silently unlocked. Only async-signal-safe calls are portable after a
multithreaded fork before exec. Additional child-side threading probes test
specific behavior; they do not remove that POSIX restriction. Already-built
binaries which import native fork directly do not gain wrapper integration.
The wrapper itself takes adapter/native locks and is not safe to invoke from
a signal handler that may have interrupted those operations. A fully
async-signal-safe _Fork backend is not provided. Native fork failures are
captured from per-Cproc errno before handlers can overwrite global errno.

## Other synchronization interfaces

POSIX semaphores are not exported by this change. An ordinary mutex-backed
counting semaphore would be easy, but sem_post must be async-signal-safe.
Taking the adapter gate could deadlock if a handler interrupted its owner.
Mach message queues alone have bounded backlog and cannot represent all
SEM_VALUE_MAX counts. A lock-free, signal-safe counter on every target or a
carefully designed independent Mach request broker is needed. Named semaphores
also need cross-process naming, lifetime and unlink semantics. No unsafe
sem_post shim is installed.

CPU-clock IDs, thread affinity, unnamed implementation-specific extensions and
robust process-shared mutexes are not supplied. These should not be inferred
from the availability of pthread.h.

## References

- NeXT libc-34.1, threads/cthreads.c, cprocs.c and stack.c, and Mach mk-108.1
  bsd/kern_sig.c: historical lifecycle, aligned stacks, errno and signal model.
- Original NEXTSTEP 3.3 SDK mach/cthreads.h, mach/thread_info.h, mach/policy.h,
  mach/message.h and machine-specific lock declarations: actual public ABI.
- [CMU C Threads manual](https://ftp.nice.ch/peanuts/GeneralData/Documents/mach/_threads.pdf):
  native package contracts and limits.
- [Darwin 0.3 libc](https://github.com/evolver56k/Darwin-0.3/tree/master/Libc-1/threads.subproj)
  and kernel-7/bsd/kern/kern_sig.c: later comparison, not a substitute for
  target runtime tests. Its Cthread layout differs from the NeXT SDK.
- [POSIX threads](https://pubs.opengroup.org/onlinepubs/7908799/xsh/threads.html)
  and [current general requirements](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html):
  cancellation ordering, ownership and supported versus optional behavior.
- [musl condition wait](https://git.musl-libc.org/cgit/musl/tree/src/thread/pthread_cond_timedwait.c)
  and pthread_cancel.c: reference for cancellation/signal races. The target
  implementation uses Mach queues, not Linux futexes or a copied signal scheme.

## Remaining work and feasible approaches

| Gap | Technical cause | Possible next step |
| --- | --- | --- |
| Native libc cancellation points | Blocking calls do not enter the managed cancellation protocol; syscall side effects and errno need careful handling. | Namespaced wrappers with qualified targeted Mach wait abortion, cancellation-state transitions and resource-transfer tests. |
| Asynchronous cancellation | Native termination bypasses cleanup; register-context injection can interrupt internal locks. | Per-architecture unwind trampolines and audited protected critical sections. |
| Per-thread Unix signals | BSD mask state is process-wide, and ordinary directed user-signal delivery is not exposed by the verified API. | Kernel support or a complete cooperative signal-virtualization design; never forward pthread_sigmask to process-wide sigprocmask. |
| Custom stacks/guards | Cproc self-identification, MIG/errno state and the native aligned allocator are private and version-sensitive. | A qualified native-compatible Mach execution backend with startup/teardown for each architecture. |
| FIFO/RR policies | Fixed-priority availability differs; priority scales, privileges, quantum semantics and pooled-worker restoration are not qualified. | Conditional native scheduling backend, with real run-queue/priority tests; do not approximate FIFO with a large timeslice. |
| Priority protocols/shared objects | Private heap state and task-local port names are insufficient for inter-process synchronization or kernel priority donation. | Appropriate kernel facilities, or a separately designed shared-memory/server protocol with stable ownership. |
| POSIX semaphores | A mutex-backed sem_post is not async-signal-safe; queue backlog alone cannot represent the required count. | Signal-safe atomic counters on every target or a dedicated Mach broker with correct lifetime/naming. |
| Complete thread-resource failure recovery | Native Cthreads has unchecked allocation paths. | Replace the launch backend while preserving libc's native per-thread environment. |
| C++ forced unwinding and TLS exit integration | Native Cthread exit uses longjmp; the compiler's C++ gthread cleanup registry is independent. | Coordinate a typed exit/unwind hook with the compiler runtime and test thread_local destructors across native-worker reuse. Ordinary C++ pthread calls and RAII on normal return are qualified, not arbitrary C++ pthread_exit/cancellation. |
| Strict clock-adjustment wake timing | Mach supplies relative millisecond receive timeouts without a verified absolute-clock notification mechanism. | Qualify a kernel clock-adjustment notification or timer facility; retain the documented bounded recheck until then. |

These are remaining implementation projects, not claims that Mach makes every
feature impossible. The implemented private synchronization/lifecycle core is
usable independently of them, subject to the documented contract.

## Building consumers

The implementation belongs to libnextstepcompat, not a separate libpthread.
Use the canonical driver or the matching development headers/import library.
Standard spellings bind to ns33_ entries through pthread.h. Configure probes
must include that header; a bare probe for a native pthread_create symbol does
not test these bindings. Availability of the header must not be used to claim
all POSIX thread feature options. The compiler's std::thread backend remains
a separate native-Cthreads integration.

EOWNERDEAD and ENOTRECOVERABLE have distinct compatibility error values outside
the original kernel's range. Native strerror may not have descriptive text for
these added values; callers can identify them using the published constants.
