/* Modern GCC threading over the native NEXTSTEP cthreads and Mach APIs.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <sys/time.h>
#include <mach/cthreads.h>
#include "gthr-nextstep.h"

_Static_assert(sizeof(__gthread_mutex_t) == sizeof(struct mutex), "native mutex ABI");
static int initialization_lock, initialized;
static void native_init(void)
{
  if (__atomic_load_n(&initialized, __ATOMIC_ACQUIRE)) return;
  spin_lock(&initialization_lock);
  if (!initialized) {
    cthread_init();
    /* Native atexit registers correctly but leaves the malloc result in its
       return register, despite the SDK's ISO int declaration. */
    atexit(__nextstep_gthread_cleanup);
    __atomic_store_n(&initialized, 1, __ATOMIC_RELEASE);
  }
  __asm__ volatile("" ::: "memory");
  *(volatile int *)&initialization_lock = 0;
}
int __gthread_active_p(void) { native_init(); return 1; }
int __gthread_mutex_init_function(__gthread_mutex_t *m)
{ memset(m, 0, sizeof(*m)); return 0; }
int __gthread_mutex_lock(__gthread_mutex_t *m)
{
  native_init();
  if (!mutex_try_lock((mutex_t)m)) mutex_wait_lock((mutex_t)m);
  return 0;
}
int __gthread_mutex_trylock(__gthread_mutex_t *m)
{ native_init(); return mutex_try_lock((mutex_t)m) ? 0 : EBUSY; }
int __gthread_mutex_unlock(__gthread_mutex_t *m)
{
  __asm__ volatile("" ::: "memory");
  *(volatile int *)&m->lock = 0;
  return 0;
}
int __gthread_mutex_destroy(__gthread_mutex_t *m)
{ return m->lock ? EBUSY : 0; }
__gthread_t __gthread_self(void) { native_init(); return cthread_self(); }
int __gthread_equal(__gthread_t a, __gthread_t b) { return a == b; }
int __gthread_yield(void) { native_init(); cthread_yield(); return 0; }

struct __nextstep_waiter {
  struct __nextstep_waiter *next;
  port_t port;
  int queued;
};
static int deadline_ms(const __gthread_time_t *deadline, unsigned *ms)
{
  struct timeval now;
  long long remaining;
  if (!deadline || deadline->tv_nsec < 0 || deadline->tv_nsec >= 1000000000L)
    return EINVAL;
  if (gettimeofday(&now, 0)) return errno;
  remaining = ((long long)deadline->tv_sec - now.tv_sec) * 1000000
              + deadline->tv_nsec / 1000 - now.tv_usec;
  if (remaining <= 0) { *ms = 0; return ETIMEDOUT; }
  remaining = (remaining + 999) / 1000;
  *ms = remaining > UINT_MAX ? UINT_MAX : (unsigned)remaining;
  return 0;
}
static void sleep_ms(unsigned ms)
{
  port_t port;
  msg_header_t message;
  if (port_allocate(task_self(), &port) != KERN_SUCCESS) { cthread_yield(); return; }
  memset(&message, 0, sizeof(message));
  message.msg_size = sizeof(message);
  message.msg_local_port = port;
  msg_receive(&message, RCV_TIMEOUT, ms);
  port_deallocate(task_self(), port);
}
int __gthread_mutex_timedlock(__gthread_mutex_t *m, const __gthread_time_t *deadline)
{
  int error;
  unsigned ms;
  for (;;) {
    error = __gthread_mutex_trylock(m);
    if (error != EBUSY) return error;
    error = deadline_ms(deadline, &ms);
    if (error) return error;
    sleep_ms(ms > 1 ? 1 : ms);
  }
}
int __gthread_recursive_mutex_init_function(__gthread_recursive_mutex_t *m)
{ memset(m, 0, sizeof(*m)); return 0; }
int __gthread_recursive_mutex_lock(__gthread_recursive_mutex_t *m)
{
  __gthread_t self = __gthread_self();
  if (__atomic_load_n(&m->owner, __ATOMIC_RELAXED) != self) {
    __gthread_mutex_lock(&m->mutex);
    __atomic_store_n(&m->owner, self, __ATOMIC_RELAXED);
    m->depth = 0;
  }
  if (m->depth == UINT_MAX) return EAGAIN;
  ++m->depth;
  return 0;
}
int __gthread_recursive_mutex_trylock(__gthread_recursive_mutex_t *m)
{
  __gthread_t self = __gthread_self();
  if (__atomic_load_n(&m->owner, __ATOMIC_RELAXED) != self) {
    int error = __gthread_mutex_trylock(&m->mutex);
    if (error) return error;
    __atomic_store_n(&m->owner, self, __ATOMIC_RELAXED);
    m->depth = 0;
  }
  if (m->depth == UINT_MAX) return EAGAIN;
  ++m->depth;
  return 0;
}
int __gthread_recursive_mutex_unlock(__gthread_recursive_mutex_t *m)
{
  if (__atomic_load_n(&m->owner, __ATOMIC_RELAXED) != __gthread_self() || !m->depth)
    return EPERM;
  if (!--m->depth) {
    __atomic_store_n(&m->owner, 0, __ATOMIC_RELAXED);
    __gthread_mutex_unlock(&m->mutex);
  }
  return 0;
}
int __gthread_recursive_mutex_destroy(__gthread_recursive_mutex_t *m)
{ return m->owner ? EBUSY : 0; }
int __gthread_recursive_mutex_timedlock(__gthread_recursive_mutex_t *m, const __gthread_time_t *deadline)
{
  int error;
  unsigned ms;
  for (;;) {
    error = __gthread_recursive_mutex_trylock(m);
    if (error != EBUSY) return error;
    error = deadline_ms(deadline, &ms);
    if (error) return error;
    sleep_ms(ms > 1 ? 1 : ms);
  }
}
int __gthread_cond_init_function(__gthread_cond_t *c)
{ memset(c, 0, sizeof(*c)); return 0; }
int __gthread_cond_destroy(__gthread_cond_t *c)
{
  int busy;
  __gthread_mutex_lock(&c->mutex);
  busy = c->head != 0;
  __gthread_mutex_unlock(&c->mutex);
  return busy ? EBUSY : 0;
}
static void remove_waiter(__gthread_cond_t *c, struct __nextstep_waiter *waiter)
{
  struct __nextstep_waiter **link = &c->head, *previous = 0;
  while (*link && *link != waiter) { previous = *link; link = &(*link)->next; }
  if (*link) {
    *link = waiter->next;
    if (c->tail == waiter) c->tail = previous;
  }
  waiter->queued = 0;
}
static int wake_one(__gthread_cond_t *c)
{
  struct __nextstep_waiter *waiter = c->head;
  msg_header_t message;
  if (!waiter) return 0;
  memset(&message, 0, sizeof(message));
  message.msg_simple = 1;
  message.msg_size = sizeof(message);
  message.msg_remote_port = waiter->port;
  if (msg_send(&message, SEND_TIMEOUT, 0) != SEND_SUCCESS) return EIO;
  remove_waiter(c, waiter);
  return 0;
}
int __gthread_cond_signal(__gthread_cond_t *c)
{
  int error;
  __gthread_mutex_lock(&c->mutex);
  error = wake_one(c);
  __gthread_mutex_unlock(&c->mutex);
  return error;
}
int __gthread_cond_broadcast(__gthread_cond_t *c)
{
  int error = 0;
  __gthread_mutex_lock(&c->mutex);
  while (c->head && !error) error = wake_one(c);
  __gthread_mutex_unlock(&c->mutex);
  return error;
}
static int condition_wait_impl(__gthread_cond_t *c, __gthread_mutex_t *m,
                               const __gthread_time_t *deadline)
{
  struct __nextstep_waiter waiter = {0};
  msg_header_t message;
  unsigned ms = 0;
  int error = 0, result;
  if (deadline && (error = deadline_ms(deadline, &ms)) != 0 && error != ETIMEDOUT) return error;
  error = 0;
  if (port_allocate(task_self(), &waiter.port) != KERN_SUCCESS) return ENOMEM;
  waiter.queued = 1;
  __gthread_mutex_lock(&c->mutex);
  if (c->tail) c->tail->next = &waiter;
  else c->head = &waiter;
  c->tail = &waiter;
  __gthread_mutex_unlock(&c->mutex);
  __gthread_mutex_unlock(m);
  for (;;) {
    memset(&message, 0, sizeof(message));
    message.msg_size = sizeof(message);
    message.msg_local_port = waiter.port;
    result = msg_receive(&message, deadline ? RCV_TIMEOUT : 0, ms);
    if (result == RCV_SUCCESS) break;
    if (result != RCV_TIMED_OUT) { error = EIO; break; }
    error = deadline_ms(deadline, &ms);
    if (error) break;
  }
  __gthread_mutex_lock(&c->mutex);
  if (waiter.queued) remove_waiter(c, &waiter);
  else error = 0; /* A signal won the timeout race under the queue lock. */
  __gthread_mutex_unlock(&c->mutex);
  port_deallocate(task_self(), waiter.port);
  __gthread_mutex_lock(m);
  return error;
}
int __gthread_cond_wait(__gthread_cond_t *c, __gthread_mutex_t *m)
{ return condition_wait_impl(c, m, 0); }
int __gthread_cond_timedwait(__gthread_cond_t *c, __gthread_mutex_t *m, const __gthread_time_t *t)
{ return condition_wait_impl(c, m, t); }
int __gthread_cond_wait_recursive(__gthread_cond_t *c, __gthread_recursive_mutex_t *m)
{
  int error;
  unsigned depth = m->depth;
  if (!depth || m->owner != __gthread_self()) return EPERM;
  m->depth = 0;
  __atomic_store_n(&m->owner, 0, __ATOMIC_RELAXED);
  error = condition_wait_impl(c, &m->mutex, 0);
  __atomic_store_n(&m->owner, __gthread_self(), __ATOMIC_RELAXED);
  m->depth = depth;
  return error;
}

int __nextstep_gthread_once_enter(__gthread_once_t *once)
{
  __gthread_mutex_lock(&once->mutex);
  while (once->state == 1) {
    int error = __gthread_cond_wait(&once->condition, &once->mutex);
    if (error) { __gthread_mutex_unlock(&once->mutex); return -error; }
  }
  if (once->state == 2) { __gthread_mutex_unlock(&once->mutex); return 0; }
  once->state = 1;
  __gthread_mutex_unlock(&once->mutex);
  return 1;
}
void __nextstep_gthread_once_finish(__gthread_once_t *once, int success)
{
  __gthread_mutex_lock(&once->mutex);
  once->state = success ? 2 : 0;
  __gthread_cond_broadcast(&once->condition);
  __gthread_mutex_unlock(&once->mutex);
}
int __gthread_once(__gthread_once_t *once, void (*function)(void))
{
  int status = __nextstep_gthread_once_enter(once);
  if (status < 0) return -status;
  if (status == 1) {
    function();
    __nextstep_gthread_once_finish(once, 1);
  }
  return 0;
}

/* Native cthreads has one application data slot, not a key API. Preserve that
   slot and maintain an independent key registry and per-thread value lists. */
struct tls_key { struct tls_key *next; __gthread_key_t id; void (*destroy)(void *); };
struct tls_value { struct tls_value *next; __gthread_key_t id; void *value; };
struct tls_thread { struct tls_thread *next; __gthread_t id; struct tls_value *values; int cleaning; };
static __gthread_mutex_t tls_lock = __GTHREAD_MUTEX_INIT;
static struct tls_key *keys;
static struct tls_thread *threads;
static __gthread_key_t last_key;
static struct tls_key *find_key(__gthread_key_t id)
{ struct tls_key *key; for (key = keys; key && key->id != id; key = key->next) {} return key; }
static struct tls_thread *find_thread(__gthread_t id)
{ struct tls_thread *t; for (t = threads; t && t->id != id; t = t->next) {} return t; }
int __gthread_key_create(__gthread_key_t *id, void (*destroy)(void *))
{
  struct tls_key *key = malloc(sizeof(*key));
  if (!key) return ENOMEM;
  __gthread_mutex_lock(&tls_lock);
  if (last_key == ULONG_MAX) { __gthread_mutex_unlock(&tls_lock); free(key); return EAGAIN; }
  key->id = ++last_key; key->destroy = destroy; key->next = keys; keys = key; *id = key->id;
  __gthread_mutex_unlock(&tls_lock);
  return 0;
}
int __gthread_key_delete(__gthread_key_t id)
{
  struct tls_key **link, *key;
  int found;
  __gthread_mutex_lock(&tls_lock);
  for (link = &keys; *link && (*link)->id != id; link = &(*link)->next) {}
  key = *link;
  if (key) *link = key->next;
  __gthread_mutex_unlock(&tls_lock);
  found = key != 0;
  free(key);
  return found ? 0 : EINVAL;
}
void *__gthread_getspecific(__gthread_key_t id)
{
  struct tls_thread *t;
  struct tls_value *v;
  void *value = 0;
  __gthread_t self = __gthread_self();
  __gthread_mutex_lock(&tls_lock);
  t = find_key(id) ? find_thread(self) : 0;
  if (t) for (v = t->values; v; v = v->next) if (v->id == id) { value = v->value; break; }
  __gthread_mutex_unlock(&tls_lock);
  return value;
}
int __gthread_setspecific(__gthread_key_t id, const void *value)
{
  struct tls_thread *t;
  struct tls_value *v;
  __gthread_t self = __gthread_self();
  __gthread_mutex_lock(&tls_lock);
  if (!find_key(id)) { __gthread_mutex_unlock(&tls_lock); return EINVAL; }
  t = find_thread(self);
  if (!t) {
    t = calloc(1, sizeof(*t));
    if (!t) { __gthread_mutex_unlock(&tls_lock); return ENOMEM; }
    t->id = self; t->next = threads; threads = t;
  }
  for (v = t->values; v && v->id != id; v = v->next) {}
  if (!v) {
    v = calloc(1, sizeof(*v));
    if (!v) { __gthread_mutex_unlock(&tls_lock); return ENOMEM; }
    v->id = id; v->next = t->values; t->values = v;
  }
  v->value = (void *)value;
  __gthread_mutex_unlock(&tls_lock);
  return 0;
}
void __nextstep_gthread_cleanup(void)
{
  __gthread_t self = __gthread_self();
  struct tls_thread *t, **link;
  struct tls_value *v, *next;
  int iteration;
  __gthread_mutex_lock(&tls_lock);
  t = find_thread(self);
  if (!t || t->cleaning) { __gthread_mutex_unlock(&tls_lock); return; }
  t->cleaning = 1;
  __gthread_mutex_unlock(&tls_lock);
  for (iteration = 0; iteration < 4; ++iteration) {
    int called = 0;
    __gthread_mutex_lock(&tls_lock);
    t = find_thread(self);
    v = t ? t->values : 0;
    while (v) {
      struct tls_key *key = find_key(v->id);
      void (*destroy)(void *) = key ? key->destroy : 0;
      void *value = v->value;
      v->value = 0;
      if (value && destroy) {
        called = 1;
        __gthread_mutex_unlock(&tls_lock);
        destroy(value);
        __gthread_mutex_lock(&tls_lock);
      }
      v = v->next;
    }
    __gthread_mutex_unlock(&tls_lock);
    if (!called) break;
  }
  __gthread_mutex_lock(&tls_lock);
  for (link = &threads; *link && (*link)->id != self; link = &(*link)->next) {}
  t = *link;
  if (t) *link = t->next;
  __gthread_mutex_unlock(&tls_lock);
  if (t) {
    for (v = t->values; v; v = next) { next = v->next; free(v); }
    free(t);
  }
}
struct start_info { void *(*function)(void *); void *argument; };
extern void __nextstep_initialize_floating_point(void);
static any_t start_thread(any_t argument)
{
  struct start_info info = *(struct start_info *)argument;
  void *result;
  free(argument);
  __nextstep_initialize_floating_point();
  result = info.function(info.argument);
  __nextstep_gthread_cleanup();
  return result;
}
int __gthread_create(__gthread_t *thread, void *(*function)(void *), void *argument)
{
  struct start_info *info;
  native_init();
  info = malloc(sizeof(*info));
  if (!info) return ENOMEM;
  info->function = function; info->argument = argument;
  *thread = cthread_fork(start_thread, info);
  if (!*thread) { free(info); return EAGAIN; }
  return 0;
}
int __gthread_join(__gthread_t thread, void **value)
{
  void *result;
  if (!thread) return EINVAL;
  if (thread == __gthread_self()) return EDEADLK;
  result = cthread_join((cthread_t)thread);
  if (value) *value = result;
  return 0;
}
int __gthread_detach(__gthread_t thread)
{ if (!thread) return EINVAL; native_init(); cthread_detach((cthread_t)thread); return 0; }

