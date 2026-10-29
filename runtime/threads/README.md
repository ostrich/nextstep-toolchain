Native threading bridge
=======================

cthreads.c implements GCC's gthread interface using the original cthreads and
Mach IPC APIs. The public types and entry points are in the compiler patch's
libgcc/gthr-nextstep.h. The C implementation includes the private original SDK
headers and checks the mutex ABI at compile time. SDK files are not bundled.

Thread creation uses a trampoline that restores the modern floating-point
precision, invokes the user function, runs key destructors, then returns to
cthreads. Both join and detach use the original thread handles. The bridge
uses the native default scheduling configuration; it does not change the
application's cthreads thread limit.

Keys have an independent registry. The cthread application data slot remains
untouched. Deleted key identifiers are not reused, preventing old per-thread
values from reappearing under a new key. Destructors run for up to four passes
and may set a new value for another pass. Foreign cthreads can use the key API,
but must call __nextstep_gthread_cleanup before returning to get destructor
cleanup. Automatic interception of arbitrary foreign thread exits is not
implemented.

Condition waits allocate a private Mach port per waiter and keep a queue under
a native mutex. Signal and timeout removal are serialized by that queue lock.
Message waits provide millisecond timeout resolution. Absolute deadlines use
gettimeofday, and are checked again after a timeout. This does not provide a
monotonic clock API. Recursive condition waits release and restore the recorded
recursion depth.

C++ once-initialization catches exceptions in an inline C++ frame, resets the
once state and rethrows. The C bootstrap path does not register an exception
frame: the SJLJ unwinder uses it to initialize its own thread-local key, so
exception-frame registration there would recursively initialize the unwinder.

Build and run tests
-------------------

From the port repository, use tests/test-gthread-backend.py with --sdk,
--arch, --compiler-build, --host-tools and --output. This builds an optimized
C foundation test independently of libstdc++. It checks identities, mutexes,
conditions, deadlines, TLS keys and cleanup, once-state transitions, and native
application-data preservation. Its build record identifies the actual inputs.

For C++ integration, build the compiler with --thread-model nextstep and the
full library with tools/build-cxx-runtime.py. Build the threads suite with
tests/test-cxx-runtime.py. Before the compiler cleanup default was updated,
this test also needed --use-cxa-atexit. Run the executable in the guest and
retain its transcript; successful compilation is not runtime validation.

Current limits
--------------

Native bridge tests pass on all four targets. The full C++ threading suite
also passes on actual NEXTSTEP 3.3 i386, m68k, SPARC and HPPA, and Intel
OPENSTEP 4.2: 18 checks, 800 concurrent exception cycles and five TLS object
destructors per run. This includes contended initialization retry, deadlines,
async/future handoff and detached-thread cleanup. These focused tests are not
proof of complete standard-library conformance or sustained application load.

HPPA builds the upstream PA sync-libfuncs family with native lock and assembler
adapters. This covers legacy synchronization operations at 1, 2, 4 and 8 bytes,
rather than only the exchange operation used by the bridge. The matching upstream libatomic build and focused atomic execution tests
are described in atomics.md. Re2c application tests pass on all four targets.
Broader conformance, additional applications and final toolchain integration
remain part of the larger runtime goal.
