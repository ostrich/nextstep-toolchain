/* Native termios ioctl adapters. SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_TERMIOS_H
#define NEXTSTEPCOMPAT_TERMIOS_H
#include_next <termios.h>
#ifdef __cplusplus
extern "C" {
#endif
int ns33_tcgetattr(int, struct termios *);
int ns33_tcsetattr(int, int, const struct termios *);
#ifdef __cplusplus
}
#endif
#define tcgetattr ns33_tcgetattr
#define tcsetattr ns33_tcsetattr
#endif
