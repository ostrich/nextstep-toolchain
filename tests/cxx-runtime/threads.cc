/* Concurrent C++ runtime integration, including exceptional initialization.
   SPDX-License-Identifier: 0BSD */
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <exception>
#include <future>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

static std::mutex lock;
static std::condition_variable ready;
static std::once_flag once;
static int started, released, increments, tls_destroyed, checks, failures;
static int static_attempts, once_attempts;
static std::vector<std::exception_ptr> exceptions;
static std::thread::id main_id;
static void check(bool okay, const char *name)
{
  ++checks;
  if (!okay) { ++failures; std::fprintf(stderr, "FAIL %s\n", name); }
}
struct LocalStatic {
  int value;
  LocalStatic() : value(73) {
    if (++static_attempts == 1) throw std::runtime_error("retry static");
  }
};
static int local_static() { static LocalStatic value; return value.value; }
struct ThreadState {
  int identity = -1;
  std::string text;
  ~ThreadState() {
    std::lock_guard<std::mutex> guard(lock);
    if (text != std::to_string(identity)) ++failures;
    ++tls_destroyed;
    ready.notify_all();
  }
};
static thread_local ThreadState state;
static thread_local int tls_integer = 19;
static void worker(int identity)
{
  state.identity = identity;
  state.text = std::to_string(identity);
  tls_integer += identity;
  {
    std::unique_lock<std::mutex> guard(lock);
    ++started;
    ready.notify_all();
    ready.wait(guard, [] { return released != 0; });
    if (std::this_thread::get_id() == main_id) ++failures;
  }
  std::fprintf(stderr, "WORKER %d barrier passed\n", identity);
  for (;;) {
    try { if (local_static() != 73) throw std::logic_error("bad static"); break; }
    catch (const std::runtime_error &) {}
  }
  std::fprintf(stderr, "WORKER %d static initialized\n", identity);
  for (;;) {
    try {
      std::call_once(once, [] {
        if (++once_attempts < 3) throw std::runtime_error("retry once");
      });
      break;
    } catch (const std::runtime_error &) {}
  }
  std::fprintf(stderr, "WORKER %d call_once initialized\n", identity);
  for (int i = 0; i < 200; ++i) {
    try {
      struct Cleanup { int *count; ~Cleanup() { ++*count; } };
      int cleanup = 0;
      try { Cleanup guard{&cleanup}; throw std::runtime_error(state.text); }
      catch (...) {
        if (cleanup != 1) throw std::logic_error("cleanup missing");
        throw;
      }
    } catch (const std::runtime_error &error) {
      std::lock_guard<std::mutex> guard(lock);
      if (state.text != error.what() || tls_integer != 19 + identity) ++failures;
      ++increments;
      if (i == 199) exceptions.push_back(std::current_exception());
    }
  }
}
int main()
{
  std::fprintf(stderr, "STAGE C++ threads\n");
  main_id = std::this_thread::get_id();
  std::vector<std::thread> threads;
  for (int i = 0; i < 4; ++i) threads.emplace_back(worker, i);
  {
    std::unique_lock<std::mutex> guard(lock);
    ready.wait(guard, [] { return started == 4; });
    released = 1;
    ready.notify_all();
  }
  std::fprintf(stderr, "STAGE joining C++ workers\n");
  for (auto &thread : threads) { thread.join(); check(!thread.joinable(), "joined state"); }
  check(increments == 800, "concurrent throw, unwind, cleanup and TLS isolation");
  check(tls_destroyed == 4, "thread-local object destructors");
  check(static_attempts == 2, "contended local static retries");
  check(once_attempts == 3, "contended call_once retries");
  check(exceptions.size() == 4, "exception_ptr handoff");
  for (auto &exception : exceptions) {
    try { std::rethrow_exception(exception); check(false, "rethrow missing"); }
    catch (const std::runtime_error &error) { check(std::string(error.what()).size() == 1, "cross-thread rethrow"); }
  }
  std::thread detached([] {
    state.identity = 9;
    state.text = "9";
  });
  detached.detach();
  {
    std::unique_lock<std::mutex> guard(lock);
    ready.wait(guard, [] { return tls_destroyed == 5; });
  }
  check(!detached.joinable(), "detach and TLS cleanup");
  std::fprintf(stderr, "STAGE C++ deadlines and futures\n");
  std::timed_mutex timed;
  timed.lock();
  bool acquired = true;
  std::thread timeout([&] { acquired = timed.try_lock_for(std::chrono::milliseconds(30)); });
  timeout.join();
  check(!acquired, "timed mutex deadline");
  timed.unlock();
  {
    std::unique_lock<std::mutex> guard(lock);
    check(ready.wait_for(guard, std::chrono::milliseconds(20)) == std::cv_status::timeout,
          "condition-variable deadline");
  }
  auto future = std::async(std::launch::async, [] { return std::string("future result"); });
  check(future.get() == "future result", "async future result");
  std::promise<int> promise;
  auto promised = promise.get_future();
  std::thread producer([&] { promise.set_value(42); });
  check(promised.get() == 42, "promise handoff");
  producer.join();
  std::printf("threads: %d checks, %d exceptions, %d TLS destructors, %d failures\n",
              checks, increments, tls_destroyed, failures);
  return failures != 0;
}
