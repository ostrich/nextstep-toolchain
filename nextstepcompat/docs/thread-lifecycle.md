# POSIX thread lifecycle

The current implementation and its native-thread ownership boundary are
explained in [POSIX threads](pthreads.md). The [API matrix](pthread-coverage.md)
records supported operations and rejected policies; [qualification](pthread-validation.md)
records the regression and stress coverage.

The expanded implementation preserves the original public object sizes,
shared function entries and managed TLS boundary. The linked API matrix and
qualification record describe lifecycle, detach, cleanup and cancellation
behavior, including the unmanaged native-thread boundary.
