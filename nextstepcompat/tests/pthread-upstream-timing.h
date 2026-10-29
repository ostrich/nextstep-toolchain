/* Test-only delays: do not depend on native process-wide alarm-based sleep.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
int ns33_test_nanosleep(const struct timespec *, struct timespec *);
unsigned ns33_test_sleep(unsigned);
#define nanosleep ns33_test_nanosleep
#define sleep ns33_test_sleep
