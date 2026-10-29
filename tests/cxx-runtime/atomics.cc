/* Atomic API and concurrent object-integrity regression.
   SPDX-License-Identifier: 0BSD */
#include <atomic>
#include <thread>
#include <stdio.h>
#include <stdint.h>

static unsigned checks, failures;
static void check(bool ok, const char *name)
{
  ++checks;
  if (!ok) { ++failures; printf("FAIL %s\n", name); }
}
template<class T> static void scalar()
{
  std::atomic<T> value(T(7));
  check(value.load() == T(7), "initial scalar load");
  value.store(T(11), std::memory_order_release);
  check(value.load(std::memory_order_acquire) == T(11), "release/acquire");
  check(value.exchange(T(13)) == T(11), "exchange");
  T expected = T(13);
  check(value.compare_exchange_strong(expected, T(17)) && expected == T(13), "CAS success");
  check(!value.compare_exchange_strong(expected, T(19)) && expected == T(17), "CAS failure updates expected");
  check(value.fetch_add(T(3)) == T(17) && value.load() == T(20), "fetch add");
  check(value.fetch_sub(T(4)) == T(20) && value.load() == T(16), "fetch sub");
  check(value.fetch_or(T(3)) == T(16) && value.load() == T(19), "fetch or");
  check(value.fetch_and(T(17)) == T(19) && value.load() == T(17), "fetch and");
  check(value.fetch_xor(T(1)) == T(17) && value.load() == T(16), "fetch xor");
  printf("ATOMIC size %u lock-free %d always %d\n", unsigned(sizeof(T)),
         int(value.is_lock_free()), int(std::atomic<T>::is_always_lock_free));
#if defined(__hppa__) || defined(__sparc__)
  check(!value.is_lock_free() && !__atomic_always_lock_free(sizeof(T), 0),
        "native lock fallback reports locked");
#endif
}
struct Triple { uint32_t a, b, c; };
struct Large { uint32_t words[9]; };
static std::atomic<unsigned> counter(0);
static std::atomic<unsigned long long> wide(0);
static std::atomic<Triple> tuple(Triple{0, ~uint32_t(0), 0x12345678});
static std::atomic<unsigned> torn(0);
static std::atomic_flag flag = ATOMIC_FLAG_INIT;
static unsigned protected_count;
static bool valid(Triple v)
{ return v.b == ~v.a && v.c == (v.a ^ 0x12345678); }
static void worker()
{
  for (unsigned i = 0; i < 1000; ++i) {
    counter.fetch_add(1, std::memory_order_relaxed);
    wide.fetch_add(1, std::memory_order_relaxed);
    Triple old = tuple.load(std::memory_order_relaxed);
    for (;;) {
      if (!valid(old)) torn.fetch_add(1);
      Triple next = {old.a + 1, ~(old.a + 1), (old.a + 1) ^ 0x12345678};
      if (tuple.compare_exchange_weak(old, next)) break;
    }
    while (flag.test_and_set(std::memory_order_acquire)) std::this_thread::yield();
    ++protected_count;
    flag.clear(std::memory_order_release);
  }
}
int main()
{
  puts("STAGE atomic scalar and aggregate API"); fflush(stdout);
  scalar<unsigned char>(); scalar<unsigned short>();
  scalar<unsigned>(); scalar<unsigned long long>();
  int array[8]; std::atomic<int *> pointer(array);
  check(pointer.fetch_add(3) == array && pointer.load() == array + 3, "pointer scaling");
  std::atomic<bool> boolean(false);
  check(!boolean.exchange(true) && boolean.load(), "bool exchange");
  Large initial = {{1,2,3,4,5,6,7,8,9}}, replacement = {{9,8,7,6,5,4,3,2,1}};
  std::atomic<Large> large(initial);
  check(large.load().words[8] == 9, "large generic load");
  check(large.compare_exchange_strong(initial, replacement), "large generic CAS");
  check(large.exchange(initial).words[8] == 1, "large generic exchange");
  large.store(replacement); check(large.load().words[0] == 9, "large generic store");
  check(!large.is_lock_free(), "large object reports locked");
  puts("STAGE concurrent atomics"); fflush(stdout);
  std::thread a(worker), b(worker), c(worker), d(worker);
  a.join(); b.join(); c.join(); d.join();
  check(counter.load() == 4000, "32-bit concurrent increments");
  check(wide.load() == 4000, "64-bit concurrent increments");
  check(tuple.load().a == 4000 && valid(tuple.load()), "aggregate concurrent CAS");
  check(torn.load() == 0, "aggregate never torn");
  check(protected_count == 4000, "atomic_flag mutual exclusion");
  printf("atomics: %u checks, 4000 updates per object, %u failures\n", checks, failures);
  return failures != 0;
}
