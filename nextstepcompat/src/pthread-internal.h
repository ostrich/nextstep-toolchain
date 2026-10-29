/* Private threading protocol. All *_locked functions require pt_gate.
   SPDX-License-Identifier: 0BSD */
#ifndef NS33_PTHREAD_INTERNAL_H
#define NS33_PTHREAD_INTERNAL_H
#include <pthread.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

struct pt_waiter {
  struct pt_waiter *next;
  port_t port;
  int sent, notified;
  void *channel;
};
struct pt_queue { struct pt_waiter *head, *tail; };
struct pt_record {
  struct pt_record *next;
  pthread_t thread;
  thread_t kernel;
  void *(*function)(void *);
  void *argument, *result;
  void *values[PTHREAD_KEYS_MAX];
  struct ns33_pthread_cleanup *cleanup;
  struct pt_waiter *waiting;
  struct pt_queue joiners;
  int joining, finished, detached, initial, exiting;
  int creating, started, start_error;
  int cancel_disabled, cancel_pending;
};
void pt_lock(void);
void pt_unlock(void);
void pt_fence(void);
struct pt_record *pt_current_locked(void);
struct pt_record *pt_find_locked(pthread_t);
int pt_cancelled_locked(struct pt_record *);
int pt_waiter_init(struct pt_waiter *);
void pt_enqueue(struct pt_queue *, struct pt_waiter *);
void pt_remove(struct pt_queue *, struct pt_waiter *);
int pt_notify(struct pt_waiter *, int);
int pt_wake(struct pt_queue *, int);
/* Drops pt_gate while receiving; reacquires it before return. Does not
   remove the waiter, destroy its port or deliver cancellation. */
int pt_wait_locked(struct pt_waiter *, const struct timespec *, int);
int pt_deadline_valid(const struct timespec *);
int pt_deadline_expired(const struct timespec *);
void pt_waiter_destroy(struct pt_waiter *);
void pt_sync_fork_child(void);
void pt_sync_thread_exit_locked(pthread_t);
void pt_extra_fork_child(void);
void pt_extra_thread_exit_locked(pthread_t);
int pt_schedule_check_locked(thread_t);
int pt_schedule_other_locked(thread_t);
int pt_attr_detached_locked(const pthread_attr_t *, int *);
#define PT_MUTEX_ATTR 0x6d750000U
#define PT_COND_ATTR 0x636f0000U
#define PT_RW_ATTR 0x72770000U
#define PT_BARRIER_ATTR 0x62610000U
#define PT_ATTR_MASK 0xffff0000U
#define PT_DESTROYED ((void *)-1)
#define PT_ENDED_OWNER ((pthread_t)-1)
#endif
