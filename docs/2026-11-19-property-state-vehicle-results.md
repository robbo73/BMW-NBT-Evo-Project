# Property and function-block state: vehicle results — 19 November 2026

The owner ran the opt-in property/state reader from the Chromebook. All
seven client-file checksums passed. Both engine-off and idling inspections
completed with the fingerprint, type, bounds and best-effort consistency
guards. No native API was invoked or target memory written.

| Observation | Engine off | Engine idling |
| --- | --- | --- |
| Current provider map entries | 15 | 15 |
| engine.RPMSpeed entry | absent | absent |
| Function-block state +0x58 | 2 | 2 |
| Early request-state gate | eligible | eligible |
| Timer handle | 0 | 0 |
| Valid proxy samples | false, false, false | false, false, false |
| Raw u16 samples | 0, 0, 0 | 0, 0, 0 |
| Interpreted RPM | null, null, null | null, null, null |
| Bytes / read calls | 2024 / 132 | 2024 / 132 |

The owner explicitly confirmed engine off for `nbt-property-state-1.json`
and supplied `nbt-property-state-idle-1.json` as an idle run. Cluster RPM
was not separately reported for this second pair. The earlier basic-cache
idle test had an owner-reported cluster value near 700 RPM. These are
different observations; no cluster agreement is established by either.

Current session identifiers, recorded for analysis only:

- HmiMain3D PID: 278582; scope 0x03a96a68.
- Provider: 0x0a336018; engine-speed proxy: 0x0a5aa930.
- Function-block host: 0x0a5a6428.
- Internal device address: 20480 / 0x5000.
- FBlock ID: 5 / 0x05; instance: 0.
- Engine-speed function ID: 3280 / 0x0cd0.
- libstdc++ base: 0x78924000; libhmiplugin: 0x78f43000;
  libhmiremoting: 0x79800000.

These are internal service identifiers, not UDS ECU/DID assignments.
Addresses are not reusable constants. Some module/heap addresses changed
from earlier reports even though the numeric PID was the same. Each reader
run obtains mappings and validates process/object state afresh.

## Interpretation

No current RPM property/bind was observed in the inspected provider, in
either engine state. Because no entry existed, no live RPM property flags
or handler list could be read. This supports missing CDS demand as a next
investigation; it does not establish creation/binding history, exclude
direct native proxy users or describe every possible provider.

The observed function block was active: its early state gate was open.
That particular readiness condition therefore was not blocking a request
in these snapshots. No request was made, so transmission, subscription
acceptance and engine-speed delivery remain unverified. Passive reads
cannot create a demand or prove that a bind would yield live data.

This function-block readiness gate is distinct from the app-admission
variant checks (0x1a0 / 0x9c56) that may affect whether an RHMI plugin is
loaded. Those current variant values have not been captured. The earlier
missing plugin mapping and standalone exit fault are also separate issues.

## Next work

Inspect the vehicle's actual libhmicoding.so offline to identify the app
admission/variant machinery, then plan a read-only check of the relevant
values if feasible. A stock library copy is sufficient for that next
analysis. These observations do not establish a reason to edit coding or
activate a plugin. Keep the paused load/unload probes paused.

Follow-up: the captured coding library has now been reviewed offline and an
opt-in observer prepared. See the [app-admission review](2026-11-19-app-admission-review.md).
Its current predicates have not yet been measured on the vehicle.

The full JSON reports remain on the owner's Chromebook. This checkpoint
transcribes the pasted reports and the engine-state clarification. No
cloud-to-vehicle connection was used and no source/library changes were
needed for these vehicle observations.
