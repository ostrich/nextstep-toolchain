/* C++ exit registry and native callback ordering.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern void _exit(int) __attribute__((noreturn));
extern int __cxa_atexit(void (*)(void *), void *, void *);
extern void __cxa_finalize(void *);
static char log_text[32];
static int used, failures;
static int first_dso, second_dso;
static const char *expected = "DACEB";
static void append(char c) { log_text[used++] = c; }
static void record(void *value)
{
  char c = *(const char *)value;
  append(c);
  if (c == 'C' && __cxa_atexit(record, "E", &second_dso)) ++failures;
}
static void native(void) { append('B'); }
static void validate(void)
{
  if (strcmp(log_text, expected)) ++failures;
  printf("atexit: order %s, %d failures\n", log_text, failures);
  fflush(stdout);
  if (failures) _exit(1);
}
int main(int argc, char **argv)
{
  atexit(validate);
  failures += __cxa_atexit(record, "A", &first_dso) != 0;
  atexit(native);
  failures += __cxa_atexit(record, "C", &second_dso) != 0;
  failures += __cxa_atexit(record, "D", &first_dso) != 0;
  if (argc == 2 && !strcmp(argv[1], "--no-finalize")) expected = "DCEBA";
  else {
    __cxa_finalize(&first_dso);
    if (strcmp(log_text, "DA")) ++failures;
    __cxa_finalize(&first_dso);
    if (strcmp(log_text, "DA")) ++failures;
  }
  return failures != 0;
}
