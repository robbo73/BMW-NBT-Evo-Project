# Registered plugin paths: vehicle results — 20 November 2026

The owner's first --inspect-manager run completed on HmiMain3D PID 278582.
It read 2488 bytes in 107 bounded calls, including the existing RPM cache
samples. The additional code fingerprints, manager type, tree/string guards
and best-effort dynamic-region rechecks completed successfully. No manager
method, scan, plugin code or native diagnostic request was invoked.

## Registered directory records

| Exact registered path | Coded-name filter |
| --- | --- |
| /opt/hmi/data/ro//Plugins | false |
| /opt/hmi/data/ro//PluginsCoded | true |
| /var/opt/hmi/data/rw//Plugins | false |
| /var/opt/hmi/data/rw//PluginsCoded | true |

The directory count was 4. The singleton address was 0x0a5686a0. Raw manager
flags +0x54 and +0x5c were both 1; their full semantics remain unproven.
The snapshot is best-effort and not atomic. None of these heap addresses
should be reused by a later command.

This confirms that the intended RW Plugins root is a registered search
path and that its record does not select the separate coded-name filter.
The doubled slash is inside the path, between directory components; it
does not justify changing the filesystem or path configuration. It results
from the recorded base path ending in a slash and the appended /Plugins
suffix. This is distinct from a special leading double-slash pathname.

Registered records do not prove that a particular directory was scanned,
that a particular manifest passed, or that initialization succeeded. The
separate global variant predicate is not bypassed by a false directory
coded-name-filter flag. The earlier admission observation found both of
its alternatives true in one cached instance, with the actual app-manager
scope association still unverified.

## Rollback and RPM state

The preceding filesystem listing showed rw -> /var/opt/hmi/data/ID5 and an
existing Plugins directory. All NbtAad names found in that RW tree were in
the hidden .nbt-rpm-stage-09902c834a37 directory, whose library size was
112119 bytes. This preserves the disabled rollback location. A fresh hash
of that file was not obtained in this session. The 112212-byte async-get
candidate remains separately reviewed on Ubuntu and was not installed.

The incidental proxy samples were again raw 0, invalid and cached_rpm=null.
Engine state was not separately confirmed, no initial get or subscription
was issued, and this is not a valid zero-RPM measurement.

## How this narrows the loading investigation

The observed roots match the original deployment location. Moving the
candidate to PluginsCoded, changing IDs/coding or editing path aliases is
not supported by these results.

The older 09902 candidate subsequently produced a rejected R_ARM_REL32
relocation and unresolved slogf during a **standalone** loader test. Its
absence from HMI after the original activation is consistent with a load
failure, but the historical HMI error itself was not captured. The slogf
provider can differ in an established HMI process, so that standalone error
must not be treated as proof of an unresolved symbol in HMI. Later source
fixes removed both required/problematic references; the current candidate
also removes unused stream initialization and adds an initial RPM get.

The separate stock-framework standalone shutdown fault and observed unit
restarts remain important. They do not establish that the current candidate
will fail in an initialized HMI, or that activating it is now safe. Further
work should review native initialization, error visibility and recovery
using the existing captures; do not repeat the standalone load/unload probe.

No additional vehicle query is required to establish these path records.
Preserve both admission/manager JSON reports on the Chromebook. The owner
can disconnect and resume offline on Ubuntu. Loading remains paused; live
CDS delivery, freshness, cluster agreement and a working RPM UI remain
unverified.

Source: the owner's pasted completed report, saved on the Chromebook as
~/bmw-idrive/nbt-plugin-manager-20261120-1.json, and the preceding pasted
filesystem listing. No direct cloud-to-vehicle connection was used.
