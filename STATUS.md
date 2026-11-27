# Project status — 26 November 2026

**Goal:** live B58 RPM on the BMW M140i's NBT Evo, without an external adapter
in normal use. **Live RPM has not been demonstrated.**

**Actual plugin loading and HMI activation/restart trials remain paused.**
The C-only endpoint/file rehearsals below are separate inert experiments.
An expired/dead endpoint can stop new discovery lookups; it does not unload
or stop code already loaded into HMI. HMI-only restart/guard-death recovery
is not a completed mechanism.

| Area | Evidence/status | Reference |
| --- | --- | --- |
| QNX SSH; external HU identification/VIN | Demonstrated; HU responses do not establish DME access | [Project README](README.md) |
| CDS-to-ShiftDeck host experiment | 24 synthetic checks pass; unchanged upstream drawing methods consume receipt-latched RPM through a fake sink. No native callback/screen or producer freshness proof | [Assessment](docs/2026-11-27-shiftdeck-integration-assessment.md) |
| Existing native gauge reference | Linked iDriveDeck releases BoostDeck/ShiftDeck; exact car framework pair listed; packaged ShiftDeck passes 50 function-prefix/vtable audit. MOST OBD RPM and stable execution on this car unverified | [27 November review](docs/2026-11-27-frezzzer-id6-review.md) |
| Direct DME communication | Unverified | [Project README](README.md) |
| Existing RPM cache, engine off/idle | Read-only observations completed; invalid cache and no RPM property in the inspected provider snapshots | [Vehicle observations](docs/2026-11-19-property-state-vehicle-results.md) |
| Native subscription versus initial async-get | Distinct paths traced offline; full RPM candidate built/reviewed, not run | [API trace](docs/2026-11-20-cds-async-get-review.md), [build](docs/2026-11-20-initial-get-build-review.md) |
| Shared per-property delegate map | Offline: same-key assignment replaces one two-word value; not a callback-count proof | [25 November map check](docs/2026-11-25-delegate-map-review.md) |
| Initialization-only candidate | Built/reviewed; five files read back in hidden stage; not activated | [Staging results](docs/2026-11-21-init-check-staging-results.md) |
| App admission/scanner configuration | Read-only cached predicates/paths observed; not proof of actual plugin admission/loading | [Admission](docs/2026-11-20-app-admission-vehicle-results.md), [paths](docs/2026-11-20-plugin-manager-vehicle-results.md) |
| C-only dummy RAM lease | Native normal deadline and explicitly delivered SIGHUP cleanup passed; not protection against guard SIGKILL | [Vehicle results](docs/2026-11-23-ram-lease-vehicle-results.md) |
| Fixed 23-byte process-owned endpoint | Native normal exit and helper SIGKILL cases passed; subsequent endpoint unavailable | [Deadline](docs/2026-11-23-endpoint-vehicle-results.md), [forced death](docs/2026-11-24-endpoint-forced-death-results.md) |
| Dummy symlink outside plugin roots | Native normal expiry and forced helper death passed, with dangling link and fixture cleanup | [Alias results](docs/2026-11-24-discovery-link-vehicle-results.md) |
| C-only stdio reader through alias | Native seek-end/ftell/rewind/full-read/close passed; both exits 0 and cleanup passed; 23-byte body only | [Reader results](docs/2026-11-24-stdio-reader-vehicle-results.md) |
| 586-byte dummy binary body | Native full stdio read/close, deadline exit 0, alias cleanup and complete trace assessment passed; three seeks and one 1024-byte request returning 586 bytes | [26 November results](docs/2026-11-26-larger-body-vehicle-results.md) |
| Larger bodies / real manifest / forced death | Native bodies above 586 bytes, real XML/HMI integration and forced provider death with an open handle remain unverified | [Build review](docs/2026-11-25-larger-body-build-review.md), [review assessment](docs/2026-11-25-larger-body-endpoint-assessment.md) |
| Held raw descriptor after normal expiry | Native 100-byte control passed; after confirmed provider exit both reads, seek and close returned -1/errno 9 promptly. Reader/provider exit 0; exact uploaded capture passes offline reassessment | [Vehicle results](docs/2026-11-26-held-expiry-vehicle-results.md) |
| Held-descriptor supervisor/capture | Native normal path passed: control-trace gate, parent release, cleanup, launcher/SSH exit 0, assessor PASS and client ACCEPT. Emergency timer/death paths untested | [Vehicle results](docs/2026-11-26-held-expiry-vehicle-results.md), [build](docs/2026-11-26-supervisor-r2-build-review.md) |
| Native loader length-error handling | Offline: ftell==-1 is not explicitly rejected; allocation call is new[], runtime consequences unverified. Current C reader already rejects it | [Static check and correction](docs/2026-11-25-larger-body-endpoint-assessment.md) |
| Earlier native framework/probe crashes | Core establishes mixed C++ stream destruction fault; binding/initialization context and associated full-unit restarts unresolved | [Core/runtime checkpoint](docs/2026-11-17-checkpoint.md) |
| Stock Sports Displays comparison | Native proxies/notification route traced offline; proposed read-only closed/open comparison not yet performed | [Stock-screen trace](docs/2026-11-20-sports-displays-requests.md) |

## Next focused work

1. The [ShiftDeck integration review and isolated host experiment](docs/2026-11-27-shiftdeck-integration-assessment.md)
   now pass 24 synthetic checks, with original draw/easing/digit methods and
   a mutex receipt latch. Repeat on Ubuntu if desired; no native rebuild is
   requested. JSON is already RPM, receipt time is not measurement freshness,
   and the upstream 750 ms baseline is not yet a CDS policy. Actual framework
   removal and Message paths have additional static evidence, but removal
   quiescence, dispatch thread, native cadence, display size and app permission
   remain unresolved. Do not adopt the upstream header or change finalizer
   return types from its declarations alone. Keep Android Auto untouched.
   The [existing upstream gauge audit](docs/2026-11-27-frezzzer-id6-review.md)
   remains supporting static evidence, not a safe-loading result; the MOST
   OBD-RPM path is unverified and deferred. Continue the separate
   [runtime-context investigation](docs/2026-11-26-runtime-context-review.md),
   with the eight-library collection still pending. No repeat inert rehearsal
   or milestone-7 edit is required now.
2. Continue the unresolved runtime/restart investigation before any HMI load.
   Endpoint expiry is a discovery constraint, not a crash fix or an unload.
3. Consider a separate bounded stock-screen observation after fingerprints,
   offsets and the script are reviewed. Valid power/torque proxies would
   support those channels, not prove that only an RPM bind is missing.

## Offline verification and reproducibility

Recorded suite counts are 25 endpoint, 21 stdio (12 reader + 9 runner),
13 discovery-link, 13 RAM-lease, 89 cache-reader and 29 init-check.
The separate larger-body preparation now has **36 host checks** after a
fortified read-hook fix. The first owner run failed two injection cases,
then the corrected owner run passed all 36 and cross-built both executables.
Nine new runner and ten trace-parser host cases also pass. These do not add
native results beyond the separately recorded 586-byte vehicle run.
The owner supplied an independent Claude report that all six suites passed
again in a scratch checkout. That is a reported third-party rerun, not a
new Codex rerun or a new vehicle result. Host checks do not emulate QNX/HMI.

The repo preserves source for the inert tools, patches and evidence notes.
The full milestone-7 app source, QNX Docker image/SDK, captured BMW libraries
and frozen candidate binaries remain separate. This checkout alone cannot
reproduce or certify the complete native dashboard. G2 integration, emulator
setup and CarPlay cluster directions remain deferred.
