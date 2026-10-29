/* Native stdio uses its original locking model; diagnostics stay in the C locale. */
#include <stdio.h>
#include <getopt.h>
#define __optpos ns33_getopt_position
#define __optreset optreset
#define __getopt_msg ns33_getopt_message
#define __lctrans_cur(s) (s)
#define FLOCK(f) ((void)0)
#define FUNLOCK(f) ((void)0)
#define weak_alias(a, b)
void ns33_getopt_message(const char *, const char *, const char *, size_t);
