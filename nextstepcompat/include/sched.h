/* Scheduling policy names for the supported pthread surface.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_SCHED_H
#define NEXTSTEPCOMPAT_SCHED_H
struct sched_param { int sched_priority; };
#define SCHED_OTHER 0
#define SCHED_FIFO 1
#define SCHED_RR 2
#ifdef __cplusplus
extern "C" {
#endif
int ns33_sched_yield(void);
int ns33_sched_get_priority_min(int);
int ns33_sched_get_priority_max(int);
#ifdef __cplusplus
}
#endif
#define sched_yield ns33_sched_yield
#define sched_get_priority_min ns33_sched_get_priority_min
#define sched_get_priority_max ns33_sched_get_priority_max
#endif
