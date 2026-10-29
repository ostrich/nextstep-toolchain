# Porting applications

Use the ordinary upstream build system. Start from a pristine release, keep
changes in patches, and separate each target's build directory and staging
root. Supply an explicit cross-compilation host triplet to configure.

Target triplets are i386-next-nextstep3.3, m68k-next-nextstep3.3,
sparc-next-nextstep3.3 and hppa-next-nextstep3.3. Set CC and CXX to the compiler
driver with the matching -arch option. Do not feed host Linux headers or
libraries to a target build. Configure checks that execute target programs
need truthful cached answers or tests on NEXTSTEP, not guessed success.

For larger projects, configure each target separately and combine matching
executables with bundled lipo. Repeated -arch works for simple builds and
sources that do not need different configure results. Do not merge libraries
or programs built with incompatible configuration choices.

Prefer optimized builds. Diagnose a failure at the right layer: application,
NextStepCompat, SDK overlay, compiler or Mach-O tools. Preserve the failing
command and a small reproducer. Successful compilation, linking or packaging
does not establish runtime correctness. Test a representative target first,
then qualify all architectures claimed in a release.

NextStepCompat is included by the existing compiler driver; inspect its
headers and documented limitations before adding application-local shims.
Fixed-address shared libraries require deliberate address assignments and
compatible export layouts. See docs/shared-libraries.md before creating one.
