# RPM cache with Sports Displays closed and open — 27 November 2026

**Both uploaded client reports record completed observations. Opening Sports
Displays did not produce a valid RPM cache sample or an RPM property entry
in the inspected provider snapshots.** This does not rule out live CDS RPM.
The reader observes existing state and never subscribes or requests a value.

## Conditions and evidence provenance

The owner was connected from Chromebook Linux over SSH, with the engine
running, and reported approximately 600 RPM at idle alongside the open-screen
result. An exact cluster value was not separately recorded for the closed
screen. The owner followed the closed-screen baseline and open-screen
comparison commands. The actual power/torque gauge readings were not supplied.

The owner subsequently uploaded all three original client JSON reports in
`nbt-sports-rpm.cIPKOg.tar.gz` (1092 bytes). Offline validation confirms the
expected three regular members, strict JSON without duplicate keys or
nonfinite numbers, identical PID/mappings and provider/property/request state,
and all six pasted sample values and timestamps. Each reported read count and
the mappings-only zero-read result also agree. No car connection or transport
replay was performed for the verification.

Archive SHA-256:

```text
8a49abe09806dcd465ab07b1ae68ed71de783079801ffbd01ca171c1f980f63e
```

The [report audit](evidence/2026-11-27-sports-rpm-report-audit.json) records
per-file sizes/hashes and the verified comparison. The original report bytes
are retained outside Git; the repository contains derived audit metadata.
These local reports do not independently authenticate screen state, cluster
RPM or the original SSH transport; those conditions remain owner-reported.

The Chromebook package's 13 SHA256SUMS entries passed. Mappings-only completed
with zero process-memory reads. Each cache run used the established
`--read-cache --inspect-property` mode, completed 132 bounded memory reads
and reported 2024 bytes read. No new target executable, library, CDS client,
plugin or diagnostic request was introduced.

## Paired result

| Field | Sports Displays closed | Sports Displays open |
| --- | --- | --- |
| HmiMain3D PID on hu-omap | 294966 | 294966 |
| Provider | 0xa232dc0 | 0xa232dc0 |
| Provider map node count | 15 | 15 |
| engine.RPMSpeed entry | absent | absent |
| RPM proxy | 0xa5e7520 | 0xa5e7520 |
| Proxy function ID | 3280 (0x0cd0) | 3280 (0x0cd0) |
| Function-block host | 0xa5e3018 | 0xa5e3018 |
| Host state at +0x58 | 2 | 2 |
| Cached validity | false in all three samples | false in all three samples |
| Raw u16 | 0 in all three samples | 0 in all three samples |
| Reported cached_rpm | null in all three samples | null in all three samples |
| Function-block pointer nonzero | true | true |
| Timer handle / value | 0 / 16000 | 0 / 16000 |
| Result | completed | completed |

Both runs reported identical module mappings: GNU C++ `0x789ac000`, coding
`0x78e9d000`, plugin `0x78f81000`, remoting `0x79800000`, and fixed-address
HMI bias zero. The same provider/proxy pointers support comparison of these
snapshots; they do not make the unlocked reads atomic.

Client monotonic sample times (not vehicle timestamps) were:

- Closed: 603891.181959536, 603891.992912168, 603892.850882755.
- Open: 603957.193424026, 603958.006198607, 603958.839865344.

The client's files are under
`~/bmw-idrive/nbt-sports-rpm.cIPKOg/`: `mappings.json`,
`sports-closed.json` and `sports-open.json`.

## Interpretation and limits

The raw zero is not a measured zero RPM: validity is false and the observer
correctly reports null. State 2 permits one early request gate to proceed;
it does not establish that a notification registration or query was sent.
The historical `registration_word_nonzero` label refers to the host pointer,
not a listener count. Absence applies to this provider at these snapshots,
not all clients, all times, or binding history.

The [stock display trace](2026-11-20-sports-displays-requests.md) identifies
separate scaling and normalized power/torque proxies at vehicle+0x369c and
vehicle+0x3728. This reader does not inspect either. Therefore this comparison
cannot establish whether those native feeds are valid, whether the stock
screen successfully receives updates, or whether RPM is the only missing
subscription. It also cannot exclude a brief change between the observations.

This is a passive RPM comparison while operating an existing screen, not an
active CDS subscribe/get test. No callback delivery, live RPM or cluster
agreement was established. Library loading and plugin/HMI activation trials
remain paused for the separate unresolved runtime/restart investigation.

## Next step

The three original client reports are now preserved and checked. No further
collection or repeat unchanged RPM comparison is requested. A power/torque comparison requires a separately
prepared observer with verified offsets, fingerprints, object guards and
offline fixtures. An active RPM test without our plugin requires an existing
external CDS client whose connection and permissions have been established.
Neither capability is supplied by this result.
