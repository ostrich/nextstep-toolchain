/* SPDX-License-Identifier: 0BSD */
#include <string>
#include <filesystem>
#include <limits>
#include <cstdio>
#include <cstdlib>

int main()
{
  unsigned checks = 0, failures = 0;
#define CHECK(value) do { ++checks; if (!(value)) { ++failures; std::printf("FAIL line %d\n", __LINE__); } } while (0)
  CHECK(std::to_string(1.25f) == "1.250000");
  CHECK(std::to_string(1.25) == "1.250000");
  CHECK(std::to_string(1.25L) == "1.250000");
  CHECK(std::to_string(-0.0L) == "-0.000000");
  CHECK(std::to_string(std::numeric_limits<double>::infinity()) == "inf");
  CHECK(std::to_string(std::numeric_limits<double>::quiet_NaN()) == "nan");
  char buffer[8];
  CHECK(std::snprintf(buffer, sizeof(buffer), "%s", "123456789") == 9);
  CHECK(std::string(buffer) == "1234567");
  std::error_code error;
  const std::filesystem::path cwd = std::filesystem::current_path(error);
  CHECK(!error && cwd.is_absolute());
  const std::filesystem::path canonical = std::filesystem::canonical(".", error);
  CHECK(!error && canonical == cwd);
  std::printf("numeric C++: %u checks, %u failures\n", checks, failures);
  return failures != 0;
}
