/* musl 1.2.6 option API with isolated NEXTSTEP compatibility state. */
#ifndef _GETOPT_H
#define _GETOPT_H

#ifdef __cplusplus
extern "C" {
#endif

int getopt(int, char * const [], const char *) __asm__("_ns33_getopt");
extern char *optarg __asm__("_ns33_optarg");
extern int optind __asm__("_ns33_optind");
extern int opterr __asm__("_ns33_opterr");
extern int optopt __asm__("_ns33_optopt");
extern int optreset __asm__("_ns33_optreset");

struct option {
	const char *name;
	int has_arg;
	int *flag;
	int val;
};

int getopt_long(int, char *const *, const char *, const struct option *, int *) __asm__("_ns33_getopt_long");
int getopt_long_only(int, char *const *, const char *, const struct option *, int *) __asm__("_ns33_getopt_long_only");

#define no_argument        0
#define required_argument  1
#define optional_argument  2

#ifdef __cplusplus
}
#endif

#endif
