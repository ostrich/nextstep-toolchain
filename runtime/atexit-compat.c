/* Itanium C++ exit registration over the original native exit callback list.
   SPDX-License-Identifier: 0BSD */
#include <stdlib.h>
#include <mach/cthreads.h>

struct exit_entry {
  struct exit_entry *next;
  void (*function)(void *);
  void *argument, *dso;
  int active;
};
static struct exit_entry *entries, *next_batch;
static int exiting;
static int exit_lock;
static void unlock(void)
{
  __asm__ volatile("" ::: "memory");
  *(volatile int *)&exit_lock = 0;
}
static void run_new_entries(void)
{
  struct exit_entry *entry;
  void (*function)(void *);
  void *argument;
  for (;;) {
    spin_lock(&exit_lock);
    for (entry = next_batch; entry && !entry->active; entry = entry->next) {}
    if (!entry) { unlock(); return; }
    entry->active = 0;
    function = entry->function;
    argument = entry->argument;
    unlock();
    function(argument);
  }
}
static void dispatch(void)
{
  struct exit_entry *entry;
  void (*function)(void *);
  void *argument;
  spin_lock(&exit_lock);
  exiting = 1;
  if (!entries) { entries = next_batch; next_batch = 0; }
  unlock();
  run_new_entries();
  spin_lock(&exit_lock);
  entry = entries;
  if (!entry) { unlock(); return; }
  entries = entry->next;
  function = entry->active ? entry->function : 0;
  argument = entry->argument;
  unlock();
  free(entry);
  if (function) function(argument);
  /* Native exit visits newly registered callbacks in a later batch. Run
     new C++ callbacks now, but retain their slots until that native batch
     arrives, so older native callbacks retain their relative positions. */
  run_new_entries();
}
int __cxa_atexit(void (*function)(void *), void *argument, void *dso)
{
  struct exit_entry *entry = malloc(sizeof(*entry));
  if (!entry) return -1;
  entry->function = function;
  entry->argument = argument;
  entry->dso = dso;
  entry->active = 1;
  spin_lock(&exit_lock);
  if (exiting) { entry->next = next_batch; next_batch = entry; }
  else { entry->next = entries; entries = entry; }
  /* Register one native slot per entry, preserving order relative to native
     callbacks too. Native atexit leaves its allocation pointer in the return
     register, so its declared int return is not an ISO status indication. */
  atexit(dispatch);
  unlock();
  return 0;
}
void __cxa_finalize(void *dso)
{
  struct exit_entry *entry;
  void (*function)(void *);
  void *argument;
  for (;;) {
    spin_lock(&exit_lock);
    for (entry = next_batch; entry; entry = entry->next)
      if (entry->active && (!dso || entry->dso == dso)) break;
    if (!entry)
      for (entry = entries; entry; entry = entry->next)
        if (entry->active && (!dso || entry->dso == dso)) break;
    if (!entry) { unlock(); return; }
    entry->active = 0;
    function = entry->function;
    argument = entry->argument;
    unlock();
    /* Keep a tombstone until its original native exit slot is consumed.
       Otherwise that slot could run a different callback out of order. */
    function(argument);
  }
}
