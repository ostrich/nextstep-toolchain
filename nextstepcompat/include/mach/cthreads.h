/* Preserve the native Cthread ABI while making its declarations usable in C++.
   The historical public struct contains a member named catch.
   SPDX-License-Identifier: 0BSD */
#ifndef NEXTSTEPCOMPAT_MACH_CTHREADS_H
#define NEXTSTEPCOMPAT_MACH_CTHREADS_H
#ifdef __cplusplus
#pragma push_macro("catch")
#undef catch
#define catch ns33_cthread_catch
extern "C" {
#endif
#include_next <mach/cthreads.h>
#ifdef __cplusplus
}
#pragma pop_macro("catch")
#endif
#endif
