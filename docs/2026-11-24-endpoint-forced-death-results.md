# Fixed-text endpoint: forced-death result — 24 November 2026

The owner reconnected from the Chromebook and the test first stopped with
`STOP: corrected RAM executable unavailable`. This is the shell preflight,
not a server failure. It establishes that the required RAM file was absent,
linked or non-executable at that check; the transcript does not establish
which condition occurred or prove a particular shutdown/reset cause.

## Restored copy and verified read-back

The guarded restore command checked the local executable against SHA-256
`83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f`,
refused an existing/linked remote destination, copied it to OMAP RAM and
set mode 700. A separate SSH request read it back to the Chromebook and
checked the same pinned hash. The owner supplied:

```text
/home/robbo73/bmw-idrive/nbt-endpoint-readback.YkSE90: OK
```

The executable path is
`/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e`.
No source or binary change was needed after the earlier normal test.

## Forced-death test passed

The owner ran the reviewed
[helper-only shell test](../tools/endpoint-rehearsal/check_forced_death.sh)
and supplied its completed output:

```text
READY pid=4141173 path=/dev/nbt_endpoint_rehearsal.4141173 bytes=23 lease_ms=10000
READ: nbt-endpoint-rehearsal
FORCED_STOP: rehearsal child 4141173
Killed
Forced-stop exit: 137 (expected 137)
PASS: endpoint unavailable after forced process death
```

The test first read the expected text, then issued SIGKILL only to its own
new helper child. The shell wait status was 137 (128 + SIGKILL). After a
brief wait, fresh `-e` and `-L` tests no longer found an accessible endpoint
at that exact path. No fallback WATCHDOG output appeared.

SIGKILL bypasses the server's explicit detach/cleanup path. This therefore
verifies endpoint unavailability after this forced process death separately
from the [23 November normal deadline/exit-0 result](2026-11-23-endpoint-vehicle-results.md).
It does not prove the global path-manager registration was physically
removed, or distinguish every possible failed-lookup cause.

## Scope and next step

This helper serves only fixed dummy text. It loads no plugin/framework,
serves no manifest, sends no RPM request and performs no HMI operation.
No HMI restart was requested. The console output does not independently
establish screen stability, behavior of already-open handles, lost-SSH
behavior or safety during a real plugin fault.

The next proposed vehicle check is a dummy discovery alias to this
process-owned endpoint, in an isolated RAM directory outside every real
Plugins/PluginsCoded root. Its preparation and review can occur offline;
no such alias trial was performed in this result. It must check new reads
through the alias before/after helper exit and cleanup of the owned alias.
Passing that check would still not authorize or prove HMI/manifest reader
compatibility, correct resource lifetime or stable C++ plugin execution.

No further BMW command is needed to preserve this checkpoint. The actual
library-loading and HMI activation/restart pause remains in effect. The
initialization-only payload remains hidden. Live B58 RPM is unverified.
