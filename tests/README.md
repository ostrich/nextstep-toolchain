# Toolchain tests and qualification

Choose checks appropriate to the component changed. These are maintainer
checks; an application port does not need to learn or run this whole suite.
Use a test script's --help for its required compiler, private SDK and output
paths. Keep generated outputs under work/ and preserve the input build identity.

## Regression checks

The test-*.py scripts here cover compiler-driver behavior, headers, linking,
archives, debug information and installed toolchains. Named subdirectories
contain fixture sources and focused compiler or shared-library suites.
For example, these release archive comparison tests need no SDK or guest:

```
python3 tests/test-release-archive.py
```

Host compilation/linking checks do not establish that the result executes on
a target. Runtime and language fixture builders emit programs for separate
guest testing. NextStepCompat's own tests live in nextstepcompat/tests/;
run its parse-host.py, path-host.py and integer-host.py directly when needed.

## Guest preparation and controls

The guest/ scripts prepare disposable Intel and Previous test guests, stage
RISC runtime batches, operate an explicitly selected console, and collect
bounded shutdown or transcript evidence. Never use a working user's desktop
or mutate an image while its emulator owns it. Supply clean stopped baselines
and private installation media explicitly. Select a Previous executable with
--emulator or provide previous on PATH.

Transport-based checks require an explicit --agent-client module and --socket.
Console controls require --console-client. RISC preparers require the external
--risc-preparer matching the selected fixtures. See the
[guest tool interface](../docs/toolchain-workflow.md#optional-guest-test-tools).

## Qualification fixtures

qualification/ contains arithmetic/vector generators, original-compiler ABI
comparisons, type probes, FlatBuffers/re2c build fixtures and evidence audits.
These support focused reproduction and larger release checks. Several consume
existing build results rather than building a complete release themselves.
Do not treat an audit of retained results as a new runtime execution.

The [validation scope](../docs/validation.md) records what has actually run.
