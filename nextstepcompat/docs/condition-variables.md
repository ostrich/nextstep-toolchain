# Condition variables

NextStepCompat provides process-private pthread conditions with default or
initialized realtime attributes. Predicates must be checked in a loop.
Initialization and destruction require caller synchronization; destroy returns
EBUSY while a waiter still uses the object, including mutex reacquisition.

Waiters use private Mach receive ports and an adapter-owned queue. Enqueue,
mutex release and notification are serialized so a wakeup cannot disappear
before the receiver sleeps. This does not modify native Cthreads' private
Cproc queues. Native condition_wait and pthread_cond_wait must not be mixed
on the same object.

Timed waits accept absolute CLOCK_REALTIME deadlines, validate nanoseconds,
and reacquire the original mutex on timeout. Pending cancellation is delivered
after reacquisition. A cancelled waiter does not consume another waiter's
notification. The queue's dynamic binding can change once all its waiters
have been unblocked, even if an old waiter is still reacquiring its mutex.
Managed robust mutex reacquisition reports owner-death/recovery errors.

Mach receives have millisecond relative timeouts. Realtime clock adjustments
are observed through bounded rechecks, with up to a one-second delay after a
large clock jump. Monotonic attributes return ENOTSUP. This distinction is
part of the [threading contract](pthreads.md), not a claim of modern kernel
timer support.

The maintained tests retain 400 broadcast handshakes using foreign native
Cthreads, and add deadlines, cancellation/signal races, mutex rebinding,
resource-failure rollback and robust reacquisition. See the [API matrix](pthread-coverage.md)
and [qualification](pthread-validation.md) for the complete scope.
