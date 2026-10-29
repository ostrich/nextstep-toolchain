/* Native terminal adapter checks. SPDX-License-Identifier: 0BSD */
#include <termios.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/time.h>

int main(void)
{
  char master[] = "/dev/ptyp0", slave[] = "/dev/ttyp0";
  struct termios original, value, observed;
  int m = -1, s, index, failure = 0;
  alarm(15);
  for (index = 0; index < 16; ++index) {
    master[9] = slave[9] = "0123456789abcdef"[index];
    m = open(master, O_RDWR);
    if (m >= 0) break;
  }
  if (m < 0) { perror("open pty master"); return 1; }
  s = open(slave, O_RDWR);
  if (s < 0) { perror("open pty slave"); close(m); return 2; }
  if (tcgetattr(s, &original)) { perror("tcgetattr"); failure = 1; goto done; }
  value = original;
  value.c_lflag ^= ECHO;
  for (index = TCSANOW; index <= TCSAFLUSH; ++index) {
    if (tcsetattr(s, index, &value) || tcgetattr(s, &observed) ||
        ((observed.c_lflag ^ value.c_lflag) & ECHO)) failure = 1;
  }
  if (tcsetattr(s, TCSANOW | TCSASOFT, &value)) failure = 1;
  if ((value.c_cflag ^ original.c_cflag) & CIGNORE) failure = 1;
  errno = 0;
  if (tcsetattr(s, 999, &value) != -1 || errno != EINVAL) failure = 1;
  errno = 0;
  if (tcgetattr(-1, &observed) != -1 || errno != EBADF) failure = 1;
  {
    char path[L_ctermid];
    cc_t byte;
    fd_set input;
    struct timeval deadline;
    value = original;
    if (cfsetispeed(&value, B9600) || cfsetospeed(&value, B19200) ||
        cfgetispeed(&value) != B9600 || cfgetospeed(&value) != B19200)
      failure = 1;
    errno = 0;
    if (cfsetispeed(&value, -1) != -1 || errno != EINVAL ||
        cfgetispeed(&value) != B9600) failure = 1;
    errno = 0;
    if (cfsetospeed(&value, B57600 + 1) != -1 || errno != EINVAL ||
        cfgetospeed(&value) != B19200) failure = 1;
    if (cfsetispeed(&value, B0) || cfgetispeed(&value) != B0) failure = 1;
    if (ctermid(path) != path || strcmp(path, "/dev/tty") ||
        strcmp(ctermid(0), "/dev/tty")) failure = 1;
    value = original;
    value.c_lflag &= ~(ICANON | ECHO);
    value.c_oflag &= ~OPOST;
    value.c_cc[VSTART] = 17;
    value.c_cc[VSTOP] = 19;
    if (tcsetattr(s, TCSANOW, &value) || tcflush(s, TCIOFLUSH)) failure = 1;
    if (tcflow(s, TCOOFF)) failure = 1;
    FD_ZERO(&input); FD_SET(m, &input);
    deadline.tv_sec = deadline.tv_usec = 0;
    if (select(m + 1, &input, 0, 0, &deadline) != 0) failure = 1;
    if (tcflow(s, TCOON) || write(s, "X", 1) != 1) failure = 1;
    FD_ZERO(&input); FD_SET(m, &input);
    deadline.tv_sec = 2; deadline.tv_usec = 0;
    if (select(m + 1, &input, 0, 0, &deadline) != 1 ||
        read(m, &byte, 1) != 1 || byte != 'X') failure = 1;
    if (tcdrain(s)) failure = 1;
    for (index = TCIOFF; index <= TCION; ++index) {
      if (tcflow(s, index)) { failure = 1; break; }
      FD_ZERO(&input); FD_SET(m, &input);
      deadline.tv_sec = 2; deadline.tv_usec = 0;
      if (select(m + 1, &input, 0, 0, &deadline) != 1 ||
          read(m, &byte, 1) != 1 || byte != (index == TCIOFF ? 19 : 17))
        failure = 1;
    }
    value.c_cc[VSTOP] = (cc_t)_POSIX_VDISABLE;
    if (tcsetattr(s, TCSANOW, &value) || tcflow(s, TCIOFF)) failure = 1;
    FD_ZERO(&input); FD_SET(m, &input);
    deadline.tv_sec = deadline.tv_usec = 0;
    if (select(m + 1, &input, 0, 0, &deadline) != 0) failure = 1;
    errno = 0;
    if (tcflow(s, 99) != -1 || errno != EINVAL) failure = 1;
    errno = 0;
    if (tcflush(s, 99) != -1 || errno != EINVAL) failure = 1;
    errno = 0;
    if (tcdrain(-1) != -1 || errno != EBADF) failure = 1;
    errno = 0;
    if (tcsendbreak(-1, 0) != -1 || errno != EBADF) failure = 1;
    errno = 0;
    if (tcsendbreak(s, 0) && errno != ENOTTY) failure = 1;
  }
  if (tcsetattr(s, TCSANOW, &original)) failure = 1;
done:
  close(s);
  close(m);
  printf("terminal adapters: %s\n", failure ? "FAIL" : "PASS");
  return failure;
}
