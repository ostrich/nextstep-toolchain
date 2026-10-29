/* POSIX threading over native Cthreads and Mach message ports.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_PTHREAD_H
#define NEXTSTEPCOMPAT_PTHREAD_H
#include <mach/cthreads.h>
#include <time.h>
#include <signal.h>
#include <sched.h>

typedef cthread_t pthread_t;
typedef unsigned long pthread_key_t;
typedef struct { unsigned int reserved; } pthread_attr_t;
typedef struct mutex pthread_mutex_t;
typedef struct condition pthread_cond_t;
typedef struct { unsigned int reserved; } pthread_condattr_t;
typedef struct { unsigned int reserved; } pthread_mutexattr_t;
typedef struct { struct mutex lock; int done; } pthread_once_t;
typedef struct { void *state; } pthread_rwlock_t;
typedef struct { unsigned int reserved; } pthread_rwlockattr_t;
typedef struct { void *state; } pthread_barrier_t;
typedef struct { unsigned int reserved; } pthread_barrierattr_t;
typedef struct mutex pthread_spinlock_t;
#define PTHREAD_KEYS_MAX 128
#define PTHREAD_DESTRUCTOR_ITERATIONS 4
#define PTHREAD_MUTEX_INITIALIZER MUTEX_INITIALIZER
#define PTHREAD_COND_INITIALIZER CONDITION_INITIALIZER
#define PTHREAD_ONCE_INIT { MUTEX_INITIALIZER, 0 }
#define PTHREAD_RWLOCK_INITIALIZER { 0 }
#define PTHREAD_CREATE_JOINABLE 0
#define PTHREAD_CREATE_DETACHED 1
#define PTHREAD_MUTEX_NORMAL 0
#define PTHREAD_MUTEX_ERRORCHECK 1
#define PTHREAD_MUTEX_RECURSIVE 2
#define PTHREAD_MUTEX_DEFAULT PTHREAD_MUTEX_NORMAL
#define PTHREAD_MUTEX_FAST_NP PTHREAD_MUTEX_NORMAL
#define PTHREAD_MUTEX_ERRORCHECK_NP PTHREAD_MUTEX_ERRORCHECK
#define PTHREAD_MUTEX_RECURSIVE_NP PTHREAD_MUTEX_RECURSIVE
#define PTHREAD_PROCESS_PRIVATE 0
#define PTHREAD_PROCESS_SHARED 1
#define PTHREAD_SCOPE_SYSTEM 0
#define PTHREAD_SCOPE_PROCESS 1
#define PTHREAD_INHERIT_SCHED 0
#define PTHREAD_EXPLICIT_SCHED 1
#define PTHREAD_PRIO_NONE 0
#define PTHREAD_PRIO_INHERIT 1
#define PTHREAD_PRIO_PROTECT 2
#define PTHREAD_MUTEX_STALLED 0
#define PTHREAD_MUTEX_ROBUST 1
#define PTHREAD_CANCEL_ENABLE 0
#define PTHREAD_CANCEL_DISABLE 1
#define PTHREAD_CANCEL_DEFERRED 0
#define PTHREAD_CANCEL_ASYNCHRONOUS 1
#define PTHREAD_CANCELED ((void *)-1)
#define PTHREAD_BARRIER_SERIAL_THREAD (-1)
#ifndef CLOCK_REALTIME
#define CLOCK_REALTIME 0
#endif
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
#endif
struct ns33_pthread_cleanup {
  struct ns33_pthread_cleanup *previous;
  void (*routine)(void *);
  void *argument;
};
#ifdef __cplusplus
extern "C" {
#endif
pthread_t ns33_pthread_self(void);
int ns33_pthread_equal(pthread_t, pthread_t);
int ns33_pthread_create(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
int ns33_pthread_join(pthread_t, void **);
int ns33_pthread_detach(pthread_t);
void ns33_pthread_exit(void *) __attribute__((noreturn));
int ns33_pthread_key_create(pthread_key_t *, void (*)(void *));
int ns33_pthread_key_delete(pthread_key_t);
void *ns33_pthread_getspecific(pthread_key_t);
int ns33_pthread_setspecific(pthread_key_t, const void *);
int ns33_pthread_once(pthread_once_t *, void (*)(void));
int ns33_pthread_cancel(pthread_t);
void ns33_pthread_testcancel(void);
int ns33_pthread_setcancelstate(int, int *);
int ns33_pthread_setcanceltype(int, int *);
int ns33_pthread_getschedparam(pthread_t, int *, struct sched_param *);
int ns33_pthread_setschedparam(pthread_t, int, const struct sched_param *);
int ns33_pthread_setschedprio(pthread_t, int);
int ns33_pthread_getconcurrency(void);
int ns33_pthread_setconcurrency(int);
int ns33_pthread_kill(pthread_t, int);
int ns33_pthread_sigmask(int, const sigset_t *, sigset_t *);
int ns33_pthread_atfork(void (*)(void), void (*)(void), void (*)(void));
int ns33_pthread_attr_init(pthread_attr_t *);
int ns33_pthread_attr_destroy(pthread_attr_t *);
int ns33_pthread_mutexattr_init(pthread_mutexattr_t *);
int ns33_pthread_mutexattr_destroy(pthread_mutexattr_t *);
int ns33_pthread_condattr_init(pthread_condattr_t *);
int ns33_pthread_condattr_destroy(pthread_condattr_t *);
int ns33_pthread_rwlockattr_init(pthread_rwlockattr_t *);
int ns33_pthread_rwlockattr_destroy(pthread_rwlockattr_t *);
int ns33_pthread_barrierattr_init(pthread_barrierattr_t *);
int ns33_pthread_barrierattr_destroy(pthread_barrierattr_t *);
int ns33_pthread_attr_getdetachstate(const pthread_attr_t *, int *);
int ns33_pthread_attr_setdetachstate(pthread_attr_t *, int);
int ns33_pthread_attr_getinheritsched(const pthread_attr_t *, int *);
int ns33_pthread_attr_setinheritsched(pthread_attr_t *, int);
int ns33_pthread_attr_getscope(const pthread_attr_t *, int *);
int ns33_pthread_attr_setscope(pthread_attr_t *, int);
int ns33_pthread_attr_getschedpolicy(const pthread_attr_t *, int *);
int ns33_pthread_attr_setschedpolicy(pthread_attr_t *, int);
int ns33_pthread_attr_getschedparam(const pthread_attr_t *, struct sched_param *);
int ns33_pthread_attr_setschedparam(pthread_attr_t *, const struct sched_param *);
int ns33_pthread_attr_getstacksize(const pthread_attr_t *, size_t *);
int ns33_pthread_attr_setstacksize(pthread_attr_t *, size_t);
int ns33_pthread_attr_getguardsize(const pthread_attr_t *, size_t *);
int ns33_pthread_attr_setguardsize(pthread_attr_t *, size_t);
int ns33_pthread_mutexattr_gettype(const pthread_mutexattr_t *, int *);
int ns33_pthread_mutexattr_settype(pthread_mutexattr_t *, int);
int ns33_pthread_mutexattr_getpshared(const pthread_mutexattr_t *, int *);
int ns33_pthread_mutexattr_setpshared(pthread_mutexattr_t *, int);
int ns33_pthread_mutexattr_getprotocol(const pthread_mutexattr_t *, int *);
int ns33_pthread_mutexattr_setprotocol(pthread_mutexattr_t *, int);
int ns33_pthread_mutexattr_getrobust(const pthread_mutexattr_t *, int *);
int ns33_pthread_mutexattr_setrobust(pthread_mutexattr_t *, int);
int ns33_pthread_mutexattr_getprioceiling(const pthread_mutexattr_t *, int *);
int ns33_pthread_mutexattr_setprioceiling(pthread_mutexattr_t *, int);
int ns33_pthread_condattr_getpshared(const pthread_condattr_t *, int *);
int ns33_pthread_condattr_setpshared(pthread_condattr_t *, int);
int ns33_pthread_condattr_getclock(const pthread_condattr_t *, clockid_t *);
int ns33_pthread_condattr_setclock(pthread_condattr_t *, clockid_t);
int ns33_pthread_rwlockattr_getpshared(const pthread_rwlockattr_t *, int *);
int ns33_pthread_rwlockattr_setpshared(pthread_rwlockattr_t *, int);
int ns33_pthread_barrierattr_getpshared(const pthread_barrierattr_t *, int *);
int ns33_pthread_barrierattr_setpshared(pthread_barrierattr_t *, int);
int ns33_pthread_attr_getstack(const pthread_attr_t *, void **, size_t *);
int ns33_pthread_attr_setstack(pthread_attr_t *, void *, size_t);
int ns33_pthread_mutex_init(pthread_mutex_t *, const pthread_mutexattr_t *);
int ns33_pthread_mutex_destroy(pthread_mutex_t *);
int ns33_pthread_cond_init(pthread_cond_t *, const pthread_condattr_t *);
int ns33_pthread_cond_destroy(pthread_cond_t *);
int ns33_pthread_rwlock_init(pthread_rwlock_t *, const pthread_rwlockattr_t *);
int ns33_pthread_rwlock_destroy(pthread_rwlock_t *);
int ns33_pthread_mutex_lock(pthread_mutex_t *);
int ns33_pthread_mutex_trylock(pthread_mutex_t *);
int ns33_pthread_mutex_unlock(pthread_mutex_t *);
int ns33_pthread_mutex_consistent(pthread_mutex_t *);
int ns33_pthread_mutex_timedlock(pthread_mutex_t *, const struct timespec *);
int ns33_pthread_mutex_getprioceiling(const pthread_mutex_t *, int *);
int ns33_pthread_mutex_setprioceiling(pthread_mutex_t *, int, int *);
int ns33_pthread_cond_signal(pthread_cond_t *);
int ns33_pthread_cond_broadcast(pthread_cond_t *);
int ns33_pthread_cond_wait(pthread_cond_t *, pthread_mutex_t *);
int ns33_pthread_cond_timedwait(pthread_cond_t *, pthread_mutex_t *, const struct timespec *);
int ns33_pthread_rwlock_rdlock(pthread_rwlock_t *);
int ns33_pthread_rwlock_wrlock(pthread_rwlock_t *);
int ns33_pthread_rwlock_tryrdlock(pthread_rwlock_t *);
int ns33_pthread_rwlock_trywrlock(pthread_rwlock_t *);
int ns33_pthread_rwlock_unlock(pthread_rwlock_t *);
int ns33_pthread_rwlock_timedrdlock(pthread_rwlock_t *, const struct timespec *);
int ns33_pthread_rwlock_timedwrlock(pthread_rwlock_t *, const struct timespec *);
int ns33_pthread_barrier_init(pthread_barrier_t *, const pthread_barrierattr_t *, unsigned);
int ns33_pthread_barrier_wait(pthread_barrier_t *);
int ns33_pthread_barrier_destroy(pthread_barrier_t *);
int ns33_pthread_spin_init(pthread_spinlock_t *, int);
int ns33_pthread_spin_lock(pthread_spinlock_t *);
int ns33_pthread_spin_trylock(pthread_spinlock_t *);
int ns33_pthread_spin_unlock(pthread_spinlock_t *);
int ns33_pthread_spin_destroy(pthread_spinlock_t *);
void ns33_pthread_cleanup_push(struct ns33_pthread_cleanup *, void (*)(void *), void *);
void ns33_pthread_cleanup_pop(struct ns33_pthread_cleanup *, int);
#ifdef __cplusplus
}
#endif
#define pthread_self ns33_pthread_self
#define pthread_equal ns33_pthread_equal
#define pthread_create ns33_pthread_create
#define pthread_join ns33_pthread_join
#define pthread_detach ns33_pthread_detach
#define pthread_exit ns33_pthread_exit
#define pthread_key_create ns33_pthread_key_create
#define pthread_key_delete ns33_pthread_key_delete
#define pthread_getspecific ns33_pthread_getspecific
#define pthread_setspecific ns33_pthread_setspecific
#define pthread_once ns33_pthread_once
#define pthread_cancel ns33_pthread_cancel
#define pthread_testcancel ns33_pthread_testcancel
#define pthread_setcancelstate ns33_pthread_setcancelstate
#define pthread_setcanceltype ns33_pthread_setcanceltype
#define pthread_getschedparam ns33_pthread_getschedparam
#define pthread_setschedparam ns33_pthread_setschedparam
#define pthread_setschedprio ns33_pthread_setschedprio
#define pthread_getconcurrency ns33_pthread_getconcurrency
#define pthread_setconcurrency ns33_pthread_setconcurrency
#define pthread_kill ns33_pthread_kill
#define pthread_sigmask ns33_pthread_sigmask
#define pthread_atfork ns33_pthread_atfork
#define pthread_attr_init ns33_pthread_attr_init
#define pthread_attr_destroy ns33_pthread_attr_destroy
#define pthread_mutexattr_init ns33_pthread_mutexattr_init
#define pthread_mutexattr_destroy ns33_pthread_mutexattr_destroy
#define pthread_condattr_init ns33_pthread_condattr_init
#define pthread_condattr_destroy ns33_pthread_condattr_destroy
#define pthread_rwlockattr_init ns33_pthread_rwlockattr_init
#define pthread_rwlockattr_destroy ns33_pthread_rwlockattr_destroy
#define pthread_barrierattr_init ns33_pthread_barrierattr_init
#define pthread_barrierattr_destroy ns33_pthread_barrierattr_destroy
#define pthread_attr_getdetachstate ns33_pthread_attr_getdetachstate
#define pthread_attr_setdetachstate ns33_pthread_attr_setdetachstate
#define pthread_attr_getinheritsched ns33_pthread_attr_getinheritsched
#define pthread_attr_setinheritsched ns33_pthread_attr_setinheritsched
#define pthread_attr_getscope ns33_pthread_attr_getscope
#define pthread_attr_setscope ns33_pthread_attr_setscope
#define pthread_attr_getschedpolicy ns33_pthread_attr_getschedpolicy
#define pthread_attr_setschedpolicy ns33_pthread_attr_setschedpolicy
#define pthread_attr_getschedparam ns33_pthread_attr_getschedparam
#define pthread_attr_setschedparam ns33_pthread_attr_setschedparam
#define pthread_attr_getstacksize ns33_pthread_attr_getstacksize
#define pthread_attr_setstacksize ns33_pthread_attr_setstacksize
#define pthread_attr_getguardsize ns33_pthread_attr_getguardsize
#define pthread_attr_setguardsize ns33_pthread_attr_setguardsize
#define pthread_mutexattr_gettype ns33_pthread_mutexattr_gettype
#define pthread_mutexattr_settype ns33_pthread_mutexattr_settype
#define pthread_mutexattr_getpshared ns33_pthread_mutexattr_getpshared
#define pthread_mutexattr_setpshared ns33_pthread_mutexattr_setpshared
#define pthread_mutexattr_getprotocol ns33_pthread_mutexattr_getprotocol
#define pthread_mutexattr_setprotocol ns33_pthread_mutexattr_setprotocol
#define pthread_mutexattr_getrobust ns33_pthread_mutexattr_getrobust
#define pthread_mutexattr_setrobust ns33_pthread_mutexattr_setrobust
#define pthread_mutexattr_getprioceiling ns33_pthread_mutexattr_getprioceiling
#define pthread_mutexattr_setprioceiling ns33_pthread_mutexattr_setprioceiling
#define pthread_condattr_getpshared ns33_pthread_condattr_getpshared
#define pthread_condattr_setpshared ns33_pthread_condattr_setpshared
#define pthread_condattr_getclock ns33_pthread_condattr_getclock
#define pthread_condattr_setclock ns33_pthread_condattr_setclock
#define pthread_rwlockattr_getpshared ns33_pthread_rwlockattr_getpshared
#define pthread_rwlockattr_setpshared ns33_pthread_rwlockattr_setpshared
#define pthread_barrierattr_getpshared ns33_pthread_barrierattr_getpshared
#define pthread_barrierattr_setpshared ns33_pthread_barrierattr_setpshared
#define pthread_attr_getstack ns33_pthread_attr_getstack
#define pthread_attr_setstack ns33_pthread_attr_setstack
#define pthread_mutex_init ns33_pthread_mutex_init
#define pthread_mutex_destroy ns33_pthread_mutex_destroy
#define pthread_cond_init ns33_pthread_cond_init
#define pthread_cond_destroy ns33_pthread_cond_destroy
#define pthread_rwlock_init ns33_pthread_rwlock_init
#define pthread_rwlock_destroy ns33_pthread_rwlock_destroy
#define pthread_mutex_lock ns33_pthread_mutex_lock
#define pthread_mutex_trylock ns33_pthread_mutex_trylock
#define pthread_mutex_unlock ns33_pthread_mutex_unlock
#define pthread_mutex_consistent ns33_pthread_mutex_consistent
#define pthread_mutex_timedlock ns33_pthread_mutex_timedlock
#define pthread_mutex_getprioceiling ns33_pthread_mutex_getprioceiling
#define pthread_mutex_setprioceiling ns33_pthread_mutex_setprioceiling
#define pthread_cond_signal ns33_pthread_cond_signal
#define pthread_cond_broadcast ns33_pthread_cond_broadcast
#define pthread_cond_wait ns33_pthread_cond_wait
#define pthread_cond_timedwait ns33_pthread_cond_timedwait
#define pthread_rwlock_rdlock ns33_pthread_rwlock_rdlock
#define pthread_rwlock_wrlock ns33_pthread_rwlock_wrlock
#define pthread_rwlock_tryrdlock ns33_pthread_rwlock_tryrdlock
#define pthread_rwlock_trywrlock ns33_pthread_rwlock_trywrlock
#define pthread_rwlock_unlock ns33_pthread_rwlock_unlock
#define pthread_rwlock_timedrdlock ns33_pthread_rwlock_timedrdlock
#define pthread_rwlock_timedwrlock ns33_pthread_rwlock_timedwrlock
#define pthread_barrier_init ns33_pthread_barrier_init
#define pthread_barrier_wait ns33_pthread_barrier_wait
#define pthread_barrier_destroy ns33_pthread_barrier_destroy
#define pthread_spin_init ns33_pthread_spin_init
#define pthread_spin_lock ns33_pthread_spin_lock
#define pthread_spin_trylock ns33_pthread_spin_trylock
#define pthread_spin_unlock ns33_pthread_spin_unlock
#define pthread_spin_destroy ns33_pthread_spin_destroy
#define pthread_cleanup_push(fn, arg) do { \
  struct ns33_pthread_cleanup ns33_cleanup_frame; \
  ns33_pthread_cleanup_push(&ns33_cleanup_frame, (fn), (arg));
#define pthread_cleanup_pop(execute) \
  ns33_pthread_cleanup_pop(&ns33_cleanup_frame, (execute)); } while (0)
#endif
