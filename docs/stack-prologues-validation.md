# NIHS hidden-argument and prologue qualification

The focused regression passed on Intel, m68k, HPPA and SPARC NEXTSTEP 3.3.
No equivalent of the Intel aggregate-result clobber was found on the other
three targets in the exercised paths. GCC patch 0014 remains Intel-specific.

## Results

Each target ran the same source at `-O1`, `-O2` and `-O3`, with
`-fstack-clash-protection`. Each executable passed 234 result/scalar checks,
plus page-spaced volatile frame checks: 702 counted checks per architecture,
2,808 across NIHS. Tests cover three aggregate sizes, six frame sizes, eight
ordinary arguments, direct-only and indirect calls, nested direct calls and
nested-function callbacks. See [the test](../tests/stack-prologues/README.md).

| Target | O1 | O2 | O3 | Native halt and filesystem checks |
| --- | --- | --- | --- | --- |
| Intel | 234/234 | 234/234 | 234/234 | Passed |
| m68k | 234/234 | 234/234 | 234/234 | Passed |
| HPPA | 234/234 | 234/234 | 234/234 | Passed |
| SPARC | 234/234 | 234/234 | 234/234 | Passed |

Intel also ran the original reproducer compiled with the pre-fix compiler.
All three aggregate rounds failed as expected and returned status 1. This
negative control confirms the batch distinguishes the original failure from
a passing corrected build; a crash would not have counted as success.

The four disposable guests ran concurrently, using QEMU for Intel/SPARC/HPPA
and the local Previous emulator for m68k. The running user guest was untouched.
No repeated application builds or general compiler-suite campaign was needed.

## ABI and generated-code audit

The audit used the maintained GCC 16.2 source and generated assembly at all
three optimization levels, rather than assuming the flag enables equivalent
protection everywhere.

| Target | Aggregate-result pointer | Nested static chain | Observed large-frame entry |
| --- | --- | --- | --- |
| Intel | EBX | ECX for the tested convention | Looped probes preserve EBX; direct-call probe uses ESI, nested-call probe uses EAX |
| m68k | A1 | A0 | Ordinary stack allocation, followed by argument preservation; no static probe loop |
| HPPA | r28 | r29 | Large-frame allocation uses r21/r1 without consuming the hidden arguments; no static probe loop |
| SPARC | Caller stack slot, read at `%fp+64` after window save | g2 | Probe loop uses g1/g4 before window save; result slot and g2 remain intact |

Intel and SPARC assembly each contains 16 looped-probe sites at every tested
optimization level. Smaller frames also exercise entries without a probe loop.
The m68k/HPPA runs qualify ordinary large-frame argument preservation; they do
not demonstrate static stack-clash protection, which those generated entries
lack. Their preserved hidden arguments are subsequently used by the function
body, and runtime checks include nested callback/trampoline execution.

Relevant GCC implementation points are `get_scratch_register_on_entry` and
`ix86_static_chain` in `gcc/config/i386/i386.cc`; `m68k_struct_value_rtx` and
`M68K_STRUCT_VALUE_REGNUM`/`STATIC_CHAIN_REGNUM` in the m68k backend;
`pa_struct_value_rtx` and the corresponding PA register macros; and
`sparc_struct_value_rtx`, `STRUCT_VALUE_OFFSET` and
`sparc_emit_probe_stack_range` in the SPARC backend.

## Scope and records

This is a focused fixed-size aggregate/static-frame regression, not proof of
all calling conventions, dynamic alloca paths, signals during probing, genuine
stack exhaustion, physical hardware behavior or complete stack-clash defense.
No additional architecture patch is warranted by these results.

The immutable compiler manifest tested was
`b914e8dc5181cdaf2591f130de9792ffe39b27915dc5a2d229b5bb4488ee5497`;
the Intel negative control used
`78bf28d526323ca41647c60350ba6c77347ad3dff8024e887983b38fd832d5a2`.
[Machine-readable results](stack-prologues-validation.json) bind the source,
build record, assembly audit, per-guest logs and collection records. Local
artifacts remain under `work/stack-prologues-nihs` in the toolchain and project
test workspace. The build script is the repeatable entry point.
