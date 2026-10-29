/* C99 facilities and their C++ wrappers, including immediate process exit.
   SPDX-License-Identifier: 0BSD */
#include <cstdlib>
#include <cstdio>
#include <string>
#include <stdexcept>
#include <limits>
#include <unistd.h>
#include <sys/wait.h>

static unsigned checks, failures;
static int callback_fd;
static void exit_callback() { (void)write(callback_fd, "A", 1); }
#define CHECK(value) do { ++checks; if (!(value)) { ++failures; std::printf("FAIL line %u\n", __LINE__); } } while (0)

int main()
{
  std::size_t end = 0;
  CHECK(std::stoll("-9223372036854775808tail", &end) == (-9223372036854775807LL-1));
  CHECK(end == 20);
  CHECK(std::stoull("18446744073709551615tail", &end) == ~0ULL);
  CHECK(end == 20);
  CHECK(std::stoll("0x7fffffffffffffff", &end, 0) == 9223372036854775807LL);
  CHECK(end == 18);
  bool caught = false;
  try { (void)std::stoll("9223372036854775808"); }
  catch (const std::out_of_range &) { caught = true; }
  CHECK(caught);
  caught = false;
  try { (void)std::stoull("no number"); }
  catch (const std::invalid_argument &) { caught = true; }
  CHECK(caught);
  CHECK(std::stof("0x1.8p+1tail", &end) == 3.0f && end == 8);
  CHECK(std::stod("1.25tail", &end) == 1.25 && end == 4);
  CHECK(std::stold("1.25tail", &end) == 1.25L && end == 4);
  volatile long long numerator = -9223372036854775807LL;
  CHECK(std::llabs(numerator) == 9223372036854775807LL);
  std::lldiv_t divided = std::lldiv(numerator, 3);
  CHECK(divided.quot == -3074457345618258602LL && divided.rem == -1);
  divided = std::lldiv(-11, -3);
  CHECK(divided.quot == 3 && divided.rem == -2);
  for (int immediate = 0; immediate != 2; ++immediate) {
  int descriptors[2];
  if (pipe(descriptors)) return 2;
  int child = fork();
  if (child < 0) return 2;
  if (!child) {
    close(descriptors[0]); callback_fd = descriptors[1];
    FILE *stream = fdopen(descriptors[1], "w");
    static char buffer[128];
    if (!stream) { std::fprintf(stderr, "fdopen failed\n"); _exit(99); }
    if (setvbuf(stream, buffer, _IOFBF, sizeof(buffer))) {
      std::fprintf(stderr, "setvbuf failed\n"); _exit(98);
    }
    // Native NeXT atexit leaves an allocation pointer in its declared int
    // return register. Verify registration through normal exit, not that value.
    std::atexit(exit_callback);
    if (std::fwrite("B", 1, 1, stream) != 1) { std::fprintf(stderr, "fwrite failed\n"); _exit(96); }
    if (immediate) std::_Exit(37);
    std::exit(37);
  }
  close(descriptors[1]);
  int status;
  int got = wait(&status);
  if (got != child || !WIFEXITED(status) || WEXITSTATUS(status) != 37)
    std::printf("child pid %d, waited %d, status %d\n", child, got, status);
  CHECK(got == child && WIFEXITED(status) && WEXITSTATUS(status) == 37);
  char bytes[3];
  unsigned count = 0;
  int length;
  while (count < sizeof(bytes) && (length = read(descriptors[0], bytes + count, sizeof(bytes) - count)) > 0)
    count += length;
  CHECK(immediate ? count == 0 : count == 2 && bytes[0] == 'A' && bytes[1] == 'B');
  close(descriptors[0]);
  }
  std::printf("C99 C++: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
