/* Validated attributes. Unsupported policies are rejected, never ignored.
   SPDX-License-Identifier: 0BSD */
#include "pthread-internal.h"
#include <mach/thread_info.h>
#include <mach/mach_host.h>

struct thread_attributes {
  struct thread_attributes *next;
  unsigned id;
  int detached, inherit;
};
static struct thread_attributes *attributes;
static unsigned next_attribute;
static int concurrency;
static struct thread_attributes *find_attr(const pthread_attr_t *a)
{
  struct thread_attributes *p;
  if (!a) return 0;
  for (p = attributes; p && p->id != a->reserved; p = p->next) {}
  return p;
}
int ns33_pthread_attr_init(pthread_attr_t *a)
{
  struct thread_attributes *p;
  if (!a) return EINVAL;
  p = calloc(1, sizeof(*p));
  if (!p) return ENOMEM;
  pt_lock();
  if (next_attribute == UINT_MAX) { pt_unlock(); free(p); return EAGAIN; }
  p->id = ++next_attribute; p->inherit = PTHREAD_INHERIT_SCHED;
  p->next = attributes; attributes = p; a->reserved = p->id;
  pt_unlock(); return 0;
}
int ns33_pthread_attr_destroy(pthread_attr_t *a)
{
  struct thread_attributes *p, **link;
  pt_lock(); p = find_attr(a);
  if (!p) { pt_unlock(); return EINVAL; }
  for (link = &attributes; *link != p; link = &(*link)->next) {}
  *link = p->next; a->reserved = 0;
  pt_unlock(); free(p); return 0;
}
int pt_attr_detached_locked(const pthread_attr_t *a, int *detached)
{
  struct thread_attributes *p;
  if (!a) { *detached = 0; return 0; }
  p = find_attr(a);
  if (!p) return EINVAL;
  *detached = p->detached; return 0;
}
#define ATTR_GET(name, field) \
int ns33_pthread_attr_get##name(const pthread_attr_t *a, int *v) \
{ struct thread_attributes *p; if (!v) return EINVAL; \
  pt_lock(); p = find_attr(a); if (p) *v = p->field; \
  pt_unlock(); return p ? 0 : EINVAL; }
#define ATTR_SET(name, field, first, second) \
int ns33_pthread_attr_set##name(pthread_attr_t *a, int v) \
{ struct thread_attributes *p; \
  if (v != first && v != second) return EINVAL; \
  pt_lock(); p = find_attr(a); if (p) p->field = v; \
  pt_unlock(); return p ? 0 : EINVAL; }
ATTR_GET(detachstate, detached)
ATTR_GET(inheritsched, inherit)
ATTR_SET(detachstate, detached, PTHREAD_CREATE_JOINABLE, PTHREAD_CREATE_DETACHED)
ATTR_SET(inheritsched, inherit, PTHREAD_INHERIT_SCHED, PTHREAD_EXPLICIT_SCHED)
static int valid_attr(const pthread_attr_t *a)
{ int valid; pt_lock(); valid = find_attr(a) != 0; pt_unlock(); return valid; }
int ns33_pthread_attr_getscope(const pthread_attr_t *a, int *v)
{ if (!v || !valid_attr(a)) return EINVAL; *v = PTHREAD_SCOPE_SYSTEM; return 0; }
int ns33_pthread_attr_setscope(pthread_attr_t *a, int v)
{
  if (!valid_attr(a) || (v != PTHREAD_SCOPE_SYSTEM && v != PTHREAD_SCOPE_PROCESS)) return EINVAL;
  return v == PTHREAD_SCOPE_SYSTEM ? 0 : ENOTSUP;
}
int ns33_pthread_attr_getschedpolicy(const pthread_attr_t *a, int *v)
{ if (!v || !valid_attr(a)) return EINVAL; *v = SCHED_OTHER; return 0; }
int ns33_pthread_attr_setschedpolicy(pthread_attr_t *a, int v)
{
  if (!valid_attr(a) || (v != SCHED_OTHER && v != SCHED_FIFO && v != SCHED_RR)) return EINVAL;
  return v == SCHED_OTHER ? 0 : ENOTSUP;
}
int ns33_pthread_attr_getschedparam(const pthread_attr_t *a, struct sched_param *v)
{ if (!v || !valid_attr(a)) return EINVAL; v->sched_priority = 0; return 0; }
int ns33_pthread_attr_setschedparam(pthread_attr_t *a, const struct sched_param *v)
{ if (!v || !valid_attr(a) || v->sched_priority) return EINVAL; return 0; }
/* Cthread self-identification depends on a native aligned stack allocation.
   Per-thread custom stack/guard changes need a native-compatible allocator,
   not merely a different Mach thread start address. Do not guess sizes. */
int ns33_pthread_attr_getstacksize(const pthread_attr_t *a, size_t *n)
{ return !n || !valid_attr(a) ? EINVAL : ENOTSUP; }
int ns33_pthread_attr_setstacksize(pthread_attr_t *a, size_t n)
{ return !valid_attr(a) || !n ? EINVAL : ENOTSUP; }
int ns33_pthread_attr_getguardsize(const pthread_attr_t *a, size_t *n)
{ return !n || !valid_attr(a) ? EINVAL : ENOTSUP; }
int ns33_pthread_attr_setguardsize(pthread_attr_t *a, size_t n)
{ (void)n; return !valid_attr(a) ? EINVAL : ENOTSUP; }
int ns33_pthread_attr_getstack(const pthread_attr_t *a, void **p, size_t *n)
{ return !p || !n || !valid_attr(a) ? EINVAL : ENOTSUP; }
int ns33_pthread_attr_setstack(pthread_attr_t *a, void *p, size_t n)
{ return !p || !n || !valid_attr(a) ? EINVAL : ENOTSUP; }

#define SIMPLE_ATTR(name, magic) \
int ns33_pthread_##name##_init(pthread_##name##_t *a) \
{ if (!a) return EINVAL; a->reserved = magic; return 0; } \
int ns33_pthread_##name##_destroy(pthread_##name##_t *a) \
{ if (!a || (a->reserved & PT_ATTR_MASK) != magic) return EINVAL; a->reserved = 0; return 0; } \
int ns33_pthread_##name##_getpshared(const pthread_##name##_t *a, int *v) \
{ if (!a || !v || (a->reserved & PT_ATTR_MASK) != magic) return EINVAL; *v = PTHREAD_PROCESS_PRIVATE; return 0; } \
int ns33_pthread_##name##_setpshared(pthread_##name##_t *a, int v) \
{ if (!a || (a->reserved & PT_ATTR_MASK) != magic || \
  (v != PTHREAD_PROCESS_PRIVATE && v != PTHREAD_PROCESS_SHARED)) return EINVAL; \
  return v == PTHREAD_PROCESS_PRIVATE ? 0 : ENOTSUP; }
SIMPLE_ATTR(mutexattr, PT_MUTEX_ATTR)
SIMPLE_ATTR(condattr, PT_COND_ATTR)
SIMPLE_ATTR(rwlockattr, PT_RW_ATTR)
SIMPLE_ATTR(barrierattr, PT_BARRIER_ATTR)
int ns33_pthread_mutexattr_gettype(const pthread_mutexattr_t *a, int *v)
{ if (!a || !v || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR) return EINVAL; *v = a->reserved & 3; return 0; }
int ns33_pthread_mutexattr_settype(pthread_mutexattr_t *a, int v)
{
  if (!a || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR ||
      (v != PTHREAD_MUTEX_NORMAL && v != PTHREAD_MUTEX_ERRORCHECK && v != PTHREAD_MUTEX_RECURSIVE)) return EINVAL;
  a->reserved = PT_MUTEX_ATTR | (a->reserved & 4) | v; return 0;
}
#define MUTEX_OPTION(name, standard, other1, other2) \
int ns33_pthread_mutexattr_get##name(const pthread_mutexattr_t *a, int *v) \
{ if (!a || !v || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR) return EINVAL; *v = standard; return 0; } \
int ns33_pthread_mutexattr_set##name(pthread_mutexattr_t *a, int v) \
{ if (!a || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR || \
 (v != standard && v != other1 && v != other2)) return EINVAL; \
 return v == standard ? 0 : ENOTSUP; }
MUTEX_OPTION(protocol, PTHREAD_PRIO_NONE, PTHREAD_PRIO_INHERIT, PTHREAD_PRIO_PROTECT)
int ns33_pthread_mutexattr_getrobust(const pthread_mutexattr_t *a, int *v)
{ if (!a || !v || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR) return EINVAL; *v = (a->reserved & 4) ? PTHREAD_MUTEX_ROBUST : PTHREAD_MUTEX_STALLED; return 0; }
int ns33_pthread_mutexattr_setrobust(pthread_mutexattr_t *a, int v)
{
  if (!a || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR ||
      (v != PTHREAD_MUTEX_STALLED && v != PTHREAD_MUTEX_ROBUST)) return EINVAL;
  a->reserved = (a->reserved & ~4U) | (v == PTHREAD_MUTEX_ROBUST ? 4 : 0); return 0;
}
int ns33_pthread_mutexattr_getprioceiling(const pthread_mutexattr_t *a, int *v)
{ return !a || !v || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR ? EINVAL : ENOTSUP; }
int ns33_pthread_mutexattr_setprioceiling(pthread_mutexattr_t *a, int v)
{ (void)v; return !a || (a->reserved & PT_ATTR_MASK) != PT_MUTEX_ATTR ? EINVAL : ENOTSUP; }
int ns33_pthread_condattr_getclock(const pthread_condattr_t *a, int *v)
{ if (!a || !v || a->reserved != PT_COND_ATTR) return EINVAL; *v = CLOCK_REALTIME; return 0; }
int ns33_pthread_condattr_setclock(pthread_condattr_t *a, int v)
{ if (!a || a->reserved != PT_COND_ATTR || (v != CLOCK_REALTIME && v != CLOCK_MONOTONIC)) return EINVAL; return v == CLOCK_REALTIME ? 0 : ENOTSUP; }
int ns33_pthread_mutex_getprioceiling(const pthread_mutex_t *m, int *v)
{ return !m || !v ? EINVAL : ENOTSUP; }
int ns33_pthread_mutex_setprioceiling(pthread_mutex_t *m, int v, int *old)
{ (void)v; (void)old; return !m ? EINVAL : ENOTSUP; }
int ns33_pthread_getconcurrency(void)
{ int n; pt_lock(); n = concurrency; pt_unlock(); return n; }
int ns33_pthread_setconcurrency(int n)
{
  if (n < 0) return EINVAL;
  /* POSIX defines a hint. Do not impose cthread_set_limit: it can prevent
     creation of a kernel worker needed to unblock an existing worker. */
  pt_lock(); concurrency = n; pt_unlock(); return 0;
}
int ns33_sched_yield(void) { (void)pthread_self(); cthread_yield(); return 0; }
int ns33_sched_get_priority_min(int policy)
{ if (policy == SCHED_OTHER) return 0; errno = policy == SCHED_FIFO || policy == SCHED_RR ? ENOTSUP : EINVAL; return -1; }
int ns33_sched_get_priority_max(int policy) { return ns33_sched_get_priority_min(policy); }
/* The supported POSIX policy has priority zero. Native dynamic priorities
   remain an implementation detail and must not be passed through as POSIX
   fixed-priority values. Hold pt_gate so the worker cannot be recycled. */
int pt_schedule_check_locked(thread_t kernel)
{
  thread_sched_info_data_t info;
  unsigned count = THREAD_SCHED_INFO_COUNT;
  if (thread_info(kernel, THREAD_SCHED_INFO, (thread_info_t)&info, &count) != KERN_SUCCESS ||
      count != THREAD_SCHED_INFO_COUNT) return ENOTSUP;
  return info.policy == POLICY_TIMESHARE ? 0 : ENOTSUP;
}
int pt_schedule_other_locked(thread_t kernel)
{
  if (!pt_schedule_check_locked(kernel)) return 0;
  if (thread_policy(kernel, POLICY_TIMESHARE, 0) != KERN_SUCCESS) return EPERM;
  return pt_schedule_check_locked(kernel);
}
int ns33_pthread_getschedparam(pthread_t t, int *policy, struct sched_param *param)
{
  struct pt_record *r;
  int error;
  if (!policy || !param) return EINVAL;
  pt_lock(); r = pt_find_locked(t);
  error = !r || r->finished ? ESRCH : pt_schedule_check_locked(r->kernel);
  if (!error) { *policy = SCHED_OTHER; param->sched_priority = 0; }
  pt_unlock(); return error;
}
int ns33_pthread_setschedparam(pthread_t t, int policy, const struct sched_param *p)
{
  struct pt_record *r;
  int error;
  if (!p || (policy != SCHED_OTHER && policy != SCHED_FIFO && policy != SCHED_RR) ||
      (policy == SCHED_OTHER && p->sched_priority)) return EINVAL;
  pt_lock(); r = pt_find_locked(t);
  error = !r || r->finished ? ESRCH :
          policy == SCHED_OTHER ? pt_schedule_other_locked(r->kernel) : ENOTSUP;
  pt_unlock(); return error;
}
int ns33_pthread_setschedprio(pthread_t t, int priority)
{ struct sched_param p; p.sched_priority = priority; return ns33_pthread_setschedparam(t, SCHED_OTHER, &p); }
int ns33_pthread_kill(pthread_t t, int sig)
{
  struct pt_record *r;
  int error;
  if (sig < 0 || sig >= NSIG) return EINVAL;
  pt_lock(); r = pt_find_locked(t);
  error = r && !r->finished ? (sig ? ENOTSUP : 0) : ESRCH;
  pt_unlock(); return error;
}
int ns33_pthread_sigmask(int how, const sigset_t *set, sigset_t *old)
{
  (void)old;
  if (set && how != SIG_BLOCK && how != SIG_UNBLOCK && how != SIG_SETMASK) return EINVAL;
  /* Native BSD masks are process-wide. A successful sigprocmask call here
     would modify other threads' masks and violate the pthread contract. */
  return ENOTSUP;
}
