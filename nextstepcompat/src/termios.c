/* Native termios ioctl adapters. SPDX-License-Identifier: 0BSD */
#include <termios.h>
#include <sys/ioctl.h>
#include <errno.h>

int ns33_tcgetattr(int fd, struct termios *term)
{
  return ioctl(fd, TIOCGETA, term);
}

int ns33_tcsetattr(int fd, int action, const struct termios *term)
{
  struct termios local;
  unsigned long request;
  int soft = action & TCSASOFT;
  switch (action & ~TCSASOFT) {
  case TCSANOW: request = TIOCSETA; break;
  case TCSADRAIN: request = TIOCSETAW; break;
  case TCSAFLUSH: request = TIOCSETAF; break;
  default: errno = EINVAL; return -1;
  }
  if (soft) {
    if (!term) { errno = EFAULT; return -1; }
    local = *term;
    local.c_cflag |= CIGNORE;
    term = &local;
  }
  return ioctl(fd, request, term);
}

/* The SDK declares these POSIX interfaces, but libsys does not export them. */
#include <unistd.h>
#include <sys/file.h>
#include <sys/time.h>
#include <stdio.h>
#include <string.h>

speed_t cfgetispeed(const struct termios *term)
{
  return term->c_ispeed;
}

speed_t cfgetospeed(const struct termios *term)
{
  return term->c_ospeed;
}

int cfsetispeed(struct termios *term, int speed)
{
  if (speed < B0 || speed > B57600) { errno = EINVAL; return -1; }
  term->c_ispeed = (speed_t)speed;
  return 0;
}

int cfsetospeed(struct termios *term, int speed)
{
  if (speed < B0 || speed > B57600) { errno = EINVAL; return -1; }
  term->c_ospeed = (speed_t)speed;
  return 0;
}

int tcdrain(int fd)
{
  return ioctl(fd, TIOCDRAIN, 0);
}

int tcflush(int fd, int queue)
{
  int flags;
  switch (queue) {
  case TCIFLUSH: flags = FREAD; break;
  case TCOFLUSH: flags = FWRITE; break;
  case TCIOFLUSH: flags = FREAD | FWRITE; break;
  default: errno = EINVAL; return -1;
  }
  return ioctl(fd, TIOCFLUSH, &flags);
}

int tcflow(int fd, int action)
{
  struct termios term;
  cc_t character;
  ssize_t result;
  switch (action) {
  case TCOOFF: return ioctl(fd, TIOCSTOP, 0);
  case TCOON: return ioctl(fd, TIOCSTART, 0);
  case TCIOFF: case TCION:
    if (ns33_tcgetattr(fd, &term)) return -1;
    character = term.c_cc[action == TCIOFF ? VSTOP : VSTART];
    if (character == (cc_t)_POSIX_VDISABLE) return 0;
    result = write(fd, &character, 1);
    if (result == 1) return 0;
    if (result == 0) errno = EIO;
    return -1;
  default: errno = EINVAL; return -1;
  }
}

int tcsendbreak(int fd, int duration)
{
  struct timeval delay;
  int result, saved;
  (void)duration; /* All durations select a quarter-second break. */
  if (ioctl(fd, TIOCSBRK, 0)) return -1;
  delay.tv_sec = 0;
  delay.tv_usec = 250000;
  result = select(0, 0, 0, 0, &delay);
  saved = errno;
  if (ioctl(fd, TIOCCBRK, 0)) return -1;
  if (result < 0) { errno = saved; return -1; }
  return 0;
}

char *ctermid(char *buffer)
{
  static char storage[L_ctermid];
  if (!buffer) buffer = storage;
  strcpy(buffer, "/dev/tty");
  return buffer;
}
