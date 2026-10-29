# Original NEXTSTEP 3.3 target evidence

The original 3.3 GCC 2.5.8 frontends can run as Intel host executables while
producing assembly for any of the four CPUs. This establishes target evidence
without needing to boot a RISC guest first. Each frontend is privately extracted
from /lib/TARGET/cc1obj, then thinned to its Intel host slice. Original files
are not modified or distributed.

## Scalar and aggregate type probes

Verified 2026-10-16 by tests/qualification/probe-native-types.py against the original target
frontends. Widths and aggregate sizes below are bytes.

| Property | Intel | m68k | SPARC | HPPA |
| --- | --- | --- | --- | --- |
| Pointer and long size | 4 | 4 | 4 | 4 |
| sizeof expression type | unsigned long | unsigned long | unsigned long | unsigned long |
| Pointer difference type | long | long | int | int |
| Wide literal element | unsigned short | unsigned short | unsigned short | unsigned short |
| Wide element size | 2 | 2 | 2 | 2 |
| long double size | 12 | 12 | 8 | 8 |
| struct { char c; double d; } size | 12 | 10 | 16 | 16 |

Type declarations are checked for compatibility by the original compiler, not
inferred solely from sizes. Scalar width/size values come from its emitted data.
For HPPA the 4.2 Intel preprocessor handles the header-free fixture, followed by
the actual original HPPA code generator. This does not require a 4.2 HPPA
compiler. The test fixture has no architecture-dependent headers.

Example, with private original frontend and an explicitly selected build guest:

```sh
python3 tests/qualification/probe-native-types.py --arch m68k --frontend /private/cc1obj-m68k --socket /private/build-agent.sock --agent-client /path/to/agent-client.py
python3 tests/qualification/probe-native-types.py --arch hppa --preprocess-arch i386 --frontend /private/cc1obj-hppa --socket /private/build-agent.sock --agent-client /path/to/agent-client.py
```

## m68k call evidence

Original 3.3 optimized output for the mixed-ABI fixture uses D0/D1 for double
returns, D0/D1 for an eight-byte aggregate, and A1 as the destination pointer
for larger aggregate returns. Arguments are stack-based. The modern target
retains the corresponding base m68k conventions and the original two-byte
member alignment. Shared NeXT target definitions must not override these with
Intel or later SVR4 conventions.

Modern -O1 switch generation exposed a separate object-format integration issue.
The original frontend loads an absolute table base into an address register and
indexes 32-bit absolute entries. Modern generic m68k assumptions about inline
PC-relative tables do not hold with the current NeXT section placement. The
restored target uses absolute entries and absolute indexed loads; the full C
matrix then passes on 3.3. The regression fixtures exercise these calls on the target system.

## SPARC call and metadata evidence

The original 3.3 frontend returns larger aggregates through the pointer at
stack offset 64, with the call/return sequence skipping the structure-size
instruction. Small scalar-mode aggregates, including the one-byte fixture,
return in an integer register. Aggregate arguments are passed indirectly.
The restored target therefore uses register struct returns where the backend
can represent the small aggregate, retaining memory returns for BLKmode.

Method metadata starts self at zero and the selector at four. Aggregate
arguments consume pointer-sized slots, and narrow values occupy the low end
of their big-endian word. For example, int/double/char encodes as
`i24@0:4i8d12c23`. This differs from Intel's stack-frame prefix and from
ordinary source type sizes.

## HPPA call and metadata evidence

The original 3.3 frontend returns the eight-byte pair through r28, rather than
the register return used by the current generic PA backend. One-byte aggregates
return in r28. Arguments up to eight bytes occupy general-register slots;
larger aggregates are indirect. Scalar floating returns use fr4. Outgoing
floating arguments must be available in both register banks because NeXT has
no SOM argument-relocation stubs. Function pointers are direct code addresses,
not HP-UX plabel descriptors. The original hard frame pointer is r4.

Fixed shared libraries can be outside short-branch range. The restored target
uses absolute ldil/ble direct calls and a direct blr/bv indirect call sequence.
NeXT assembly uses backtick field selectors, numeric r30 for the stack pointer,
.long/.short data and ordinary Mach-O sections. SOM imports, call descriptors,
procedure directives, global-pointer data addressing and branch-table markers
are inapplicable.

HPPA method arguments grow downward. Eight-byte slots require alignment,
indirect aggregates consume a pointer, and narrow arguments retain their
actual byte offsets. The int/double/char fixture encodes as
`i25@-4:-8i-12d-24c-25`. The checked-in argument-layout fixture and expectations
cover five original method signatures on each RISC target, including narrow
values, aggregates, mixed floats and stack arguments. Both modern Objective-C
frontends must reproduce those strings. This checks metadata compatibility,
not actual forwarding execution.


## RISC runtime corrections

Original NS3.3 execution confirms the SPARC NeXT convention: register-mode
aggregates no larger than one word use integer return registers, including a
single float field. BLKmode aggregates and larger aggregates use the stack
result slot and the memory-return call sequence. The generic SPARC backend's
PCC default override violated the first rule, causing corruption/bus errors
when an original caller did not provide a hidden result pointer. Merely
changing the header default was insufficient. The NeXT-specific override now
preserves the default, size/mode boundary and integer register bank.

Native/modern callers and callees now pass the original 32-check mixed-C suite
at four optimization levels and two additional 18-check aggregate-boundary
programs. The native-only 32-check control also passes. The extra fixture
covers one/two/four-byte scalar fields, three-byte and two-byte arrays,
two-word records, two-halfword records, and single float/double fields.

The HPPA 3.3 runtime's method_getArgumentInfo returns encoded negative offsets,
not offsets relative to self. For i16@-4:-8i-12i-16 it returns self=-4 and the
last argument=-16. Both original and modern callers observe this on original
and modern classes. The test expectation was corrected without changing
encodings. Both modern Objective-C language suites now pass all 52 checks.
