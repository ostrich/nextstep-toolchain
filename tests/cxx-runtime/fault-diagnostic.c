/* Test-only native signal context capture, installed before library startup.
   SPDX-License-Identifier: 0BSD */
#if defined(__sparc__)
#include <sparc/signal.h>
#elif defined(__hppa__)
#include <hppa/signal.h>
#else
#error This diagnostic currently supports the RISC test guests
#endif
extern int write(int, const void *, unsigned);
extern void _exit(int) __attribute__((noreturn));
struct diagnostic_sigvec { void (*handler)(); int mask; int flags; };
extern int sigvec(int, struct diagnostic_sigvec *, struct diagnostic_sigvec *);
static void hex(unsigned value)
{
  char text[9];
  int i;
  for (i = 7; i >= 0; --i) { text[i] = "0123456789abcdef"[value & 15]; value >>= 4; }
  text[8] = '\n';
  write(2, text, sizeof(text));
}
#ifdef TEST_LOCALE_STATE
extern void *classic __asm__("__ZNSt6locale10_S_classicE");
extern void *global __asm__("__ZNSt6locale9_S_globalE");
static void locale_state(void)
{
  write(2, "LOCALE classic/global\n", 22);
  hex((unsigned)classic); hex((unsigned)global);
}
#else
static void locale_state(void) {}
#endif
static void fault(int signal, int code, struct sigcontext *context)
{
  write(2, "FAULT signal/code/pc/sp\n", 24);
  hex(signal); hex(code);
#if defined(__sparc__)
  hex(context->sc_pc); hex(context->sc_sp);
#elif defined(__hppa__)
  hex(context->sc_pcoq[0]); hex(context->sc_sp);
#endif
  locale_state();
  _exit(128 + signal);
}
static void __attribute__((constructor)) install_diagnostic(void)
{
  struct diagnostic_sigvec vector = { (void (*)())fault, 0, 0 };
  if (sigvec(11, &vector, 0) || sigvec(10, &vector, 0))
    _exit(120);
  write(2, "FAULT diagnostics ready\n", 24);
  locale_state();
}
