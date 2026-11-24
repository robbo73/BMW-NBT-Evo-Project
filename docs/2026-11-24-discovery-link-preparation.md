# Dummy discovery-link preparation — 24 November 2026

The [native endpoint forced-death test](2026-11-24-endpoint-forced-death-results.md)
passed. The next bounded experiment tests followed lookup/read behavior
through a symlink to the same process-served endpoint. It remains isolated
from real discovery roots and all manifest/plugin/HMI operations.

## Prepared deliverable

[Source, instructions and fixture tests](../tools/discovery-link-rehearsal/README.md)
are available in the repository. The separately delivered ready archive
contains those five source/document/metadata files, a checksum list and the
unchanged 13876-byte endpoint binary; no new QNX compilation is needed.
No binary, BMW library or SDK output is committed here.

| Item | SHA-256 |
| --- | --- |
| check_discovery_link.sh | 91562e122f4c3a7a9cbad626f06425fc016c2cea5c55139ff200b3349fa269ce |
| Existing endpoint binary | 83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f |
| nbt-discovery-link-ready.tar.gz (13072 bytes) | 98158650111b5679997da7293a4c6155530a173f066b9c38de3251d792e6b87d |

The tar member list contains only one root directory and seven ordinary
files. Every archived file matches the embedded SHA256SUMS. The packaged
verification script passed checksum verification, POSIX shell syntax and
all 13 Linux control-flow fixtures. It never executes the ARM binary or
contacts the BMW. Owner-side Ubuntu verification is the next step.

## Target behavior and limits

Default/help performs no writes. Explicit deadline/forced-death modes would
use only /ramdisk/mm/.nbt-endpoint-alias.<shell-pid>/dummy-discovery.txt,
a unique link to the new child helper's fixed-text endpoint. They require a
successful alias read, the expected helper exit (0 or 137), a remaining
symlink whose followed target is unavailable, and owned-fixture cleanup.
Only that newly spawned helper can be signalled by the script/fallback.
There is no caller-selected path/PID, payload move or .manifest filename.

Cleanup unlinks its own alias without following the target; a non-link
replacement or unexpected directory entry is preserved and causes failure.
The exact directory must remain non-linked and empty before rm -r is used.
Shell SIGKILL can leave a dummy RAM fixture, because no shell trap runs then.
The script is not a general recovery mechanism and must not be placed in a
real Plugins directory. No real HMI process is watched or signalled.

Linux tests exercise branch and cleanup logic using ordinary files and
shorter test sleeps. The positive forced-death branch test uses an explicit
external file unlinker; the corresponding negative test rejects a surviving
ordinary file. Neither models QNX namespace/IPC or establishes new vehicle
results. Further cases cover default/bad arguments, missing/linked binary,
linked root, alias text, missing endpoint, hidden-entry preservation, hangup,
closed stdout and overrun failure.

The alias trial has not run on the BMW. Native scan/manifest reader behavior,
resource and open-handle lifetimes, actual SSH-loss behavior and HMI-fault
containment remain unverified. The existing initialization-only candidate
remains hidden; library-load/HMI activation and restart trials remain paused.
Live B58 RPM has not been demonstrated.


## Follow-up

The owner completed Ubuntu integrity verification and all 13 host checks,
then passed the native normal-expiry dummy alias test. See the
[vehicle results](2026-11-24-discovery-link-vehicle-results.md) for the exact
read-back and console evidence. The owner subsequently passed the forced-
death alias branch as well: expected text, SIGKILL wait status 137, a dangling
alias and owned-fixture cleanup. Both dummy alias cases now pass; no manifest
or HMI integration has been tested.
The frozen package/source checksums are unchanged.
