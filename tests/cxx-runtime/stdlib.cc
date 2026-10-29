/* SPDX-License-Identifier: 0BSD */
#include <cstdio>
#include <algorithm>
#include <chrono>
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <unordered_map>
#include <vector>

static int checks, failures;
static void check(bool okay, const char *name)
{
  ++checks;
  if (!okay) { ++failures; std::cerr << "FAIL " << name << '\n'; }
}

static void containers()
{
  std::string large(8192, 'a');
  large.replace(4096, 4, "NEXT");
  check(large.substr(4096, 4) == "NEXT", "large string replace");
  std::vector<int> numbers;
  for (int i = 999; i >= 0; --i) numbers.push_back(i);
  std::sort(numbers.begin(), numbers.end());
  check(std::is_sorted(numbers.begin(), numbers.end()), "vector sort");
  check(std::accumulate(numbers.begin(), numbers.end(), 0) == 499500, "accumulate");
  check(std::binary_search(numbers.begin(), numbers.end(), 731), "binary search");
  std::map<std::string, int> ordered;
  std::unordered_map<std::string, int> hashed;
  for (int i = 0; i != 500; ++i) {
    std::string key = std::to_string(i);
    ordered[key] = i;
    hashed[key] = i;
  }
  check(ordered.at("247") == 247 && hashed.at("499") == 499, "associative containers");
  std::set<int> unique(numbers.begin(), numbers.end());
  check(unique.size() == 1000 && unique.count(319) == 1, "set");
  try { (void)numbers.at(1000); check(false, "vector bounds exception missing"); }
  catch (const std::out_of_range &error) {
    check(std::string(error.what()).find("vector") != std::string::npos, "standard exception message");
  }
  try { (void)ordered.at("missing"); check(false, "map bounds exception missing"); }
  catch (const std::out_of_range &) { check(true, "map bounds exception"); }
}

static void streams(const char *input_file)
{
  std::ostringstream out;
  out << 12345 << ' ' << std::hex << 255 << ' ' << std::fixed << std::setprecision(3) << 1.25;
  check(out.str() == "12345 ff 1.250", "formatted output");
  std::istringstream input("-12345 1.25 hello");
  int number = 0;
  double real = 0;
  std::string word;
  input >> number >> real >> word;
  check(number == -12345 && real == 1.25 && word == "hello", "formatted input");
  std::ostringstream extended;
  extended << std::setprecision(20) << (1.0L / 3.0L);
  check(extended.str().find("0.333333333333") == 0, "long double output");
  char converted[128];
  const auto result = std::to_chars(converted, converted + sizeof(converted),
                                    1.0L / 3.0L, std::chars_format::general, 21);
  check(result.ec == std::errc{} && std::string(converted, result.ptr).find("0.333333333333") == 0,
        "long double to_chars");
  std::istringstream invalid("hello");
  invalid.exceptions(std::ios::failbit);
  try { invalid >> number; check(false, "stream exception missing"); }
  catch (const std::ios_base::failure &) { check(true, "stream exception"); }
  std::ifstream kernel(input_file, std::ios::binary);
  char header[4];
  kernel.read(header, 4);
  check(kernel.gcount() == 4, "native file read");
  kernel.seekg(0, std::ios::end);
  check(kernel.tellg() > std::streamoff(4096), "native file seek");
}

static void algorithms_and_os(const std::string &directory, const char *input_file)
{
  std::regex expression("([a-z]+)-([0-9]+)");
  std::smatch match;
  std::string text("nextstep-33");
  check(std::regex_match(text, match, expression) && match[2] == "33", "regex captures");
  check(std::regex_replace(text, expression, "$2:$1") == "33:nextstep", "regex replacement");
  try { std::regex invalid("["); check(false, "regex exception missing"); }
  catch (const std::regex_error &) { check(true, "regex exception"); }
  const auto now = std::chrono::system_clock::now();
  check(now.time_since_epoch() > std::chrono::hours(24 * 365 * 30), "wall clock");
  namespace fs = std::filesystem;
  check(fs::path("/private/./tmp/../var").lexically_normal() == "/private/var", "path normalization");
  check(fs::is_regular_file(input_file) && fs::file_size(input_file) > 4096, "native file metadata");
  int entries = 0;
  for (const auto &entry: fs::directory_iterator("/")) {
    check(!entry.path().filename().empty(), "directory entry");
    ++entries;
  }
  check(entries > 4, "native directory iteration");
  if (directory == "--read-only") {
    std::cout << "WRITE_TESTS_NOT_RUN\n";
    return;
  }
  const auto folder = fs::path(directory) / "stdlib-files";
  std::fprintf(stderr, "STAGE filesystem create directory\n");
  fs::create_directory(folder);
  const auto file = folder / "state.bin";
  std::fprintf(stderr, "STAGE filesystem write\n");
  { std::ofstream output(file, std::ios::binary); output << "NEXTSTEP 3.3\n"; }
  check(fs::file_size(file) == 13, "file create and write");
  const auto copied = folder / "copy.bin";
  std::fprintf(stderr, "STAGE filesystem copy\n");
  fs::copy_file(file, copied);
  check(fs::file_size(copied) == 13, "file copy");
  std::fprintf(stderr, "STAGE filesystem rename\n");
  fs::rename(copied, folder / "renamed.bin");
  check(fs::exists(folder / "renamed.bin"), "file rename");
  std::fprintf(stderr, "STAGE filesystem remove\n");
  check(fs::remove_all(folder) == 3, "file removal");
}

int main(int argc, char **argv)
{
  if (argc != 2 && argc != 3) { std::cerr << "usage: stdlib-test SCRATCH_DIRECTORY|--read-only [INPUT_FILE]\n"; return 2; }
  const char *input_file = argc == 3 ? argv[2] : "/mach_kernel";
  try {
    std::fprintf(stderr, "STAGE containers\n");
    containers();
    std::fprintf(stderr, "STAGE streams\n");
    streams(input_file);
    std::fprintf(stderr, "STAGE algorithms and OS\n");
    algorithms_and_os(argv[1], input_file);
  }
  catch (const std::exception &error) { check(false, error.what()); }
  std::cout << "stdlib: " << checks << " checks, " << failures << " failures\n";
  return failures != 0;
}
