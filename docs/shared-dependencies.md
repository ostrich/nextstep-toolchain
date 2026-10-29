# Fixed-address shared dependencies

The historical mkshlib constructor writes LC_LOADFVMLIB references into the
import archive. A runtime produced as MH_FVMLIB cannot itself consume those
load commands. The constructor therefore resolves references at fixed export
addresses without embedding dependency implementations, and carries the full
runtime closure in the link-time import archive.

Pass each dependency import archive with --dependency to nextstep-shlib.
Consumers link the top-level import archive through ordinary -L/-l options.
Its identity members ensure that the final executable loads every required
runtime and reserves each library's complete ABI ranges.

Conflicting identities, overlapping reservations, duplicate exports, missing
target slices, malformed records and dependency cycles are rejected. Compatible
minor requirements merge to the highest floor only when identity and mapping
information agree. Constructor inputs and dependency records are hashed in
the build record. Caller import archives are not modified.

## Tests

tests/shared-libraries/test-dependencies.py constructs a diamond graph and
checks identities, closure, reservations and failures on all four targets.
Native tests cover baseline execution, missing transitive dependencies,
insufficient minor versions, compatible replacement without relinking and
restoration. A changed leaf result is observed through both branches, so the
upgrade test establishes actual use of the replacement library.

The shared compatibility runtime has an additional environment constraint:
its environ reference must use the system runtime's executable-owned pointer.
A private duplicate would break native getenv and direct environ replacement.
nextstepcompat/build-shared.py implements this bridge and preserves the export
slots in nextstepcompat/shared.json.

See [shared-library construction](shared-libraries.md) for specifications and
[NextStepCompat](../nextstepcompat/README.md) for compatibility API contracts.
