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
| Larger bodies / real manifest / open-handle death | Native bodies above 586 bytes, real XML/HMI integration and provider death with an open handle remain unverified | [Build review](docs/2026-11-25-larger-body-build-review.md), [review assessment](docs/2026-11-25-larger-body-endpoint-assessment.md) |
| Held-descriptor reader | Owner cross-build and 22 host checks pass; static imports/ABI/control flow reviewed. No native run yet; the separately reviewed supervisor is now packaged. Offline assessor has 50 synthetic checks | [Build review](docs/2026-11-26-open-handle-reader-build-review.md) |
| Held-descriptor supervisor/capture | Owner host suite 50/50; QNX static build review passes; ready bundle/client prepared. No native supervisor/held-reader result | [Build and bundle](docs/2026-11-26-supervisor-r2-build-review.md) |
| Native loader length-error handling | Offline: ftell==-1 is not explicitly rejected; allocation call is new[], runtime consequences unverified. Current C reader already rejects it | [Static check and correction](docs/2026-11-25-larger-body-endpoint-assessment.md) |
| Earlier native framework/probe crashes | Core establishes mixed C++ stream destruction fault; binding/initialization context and associated full-unit restarts unresolved | [Core/runtime checkpoint](docs/2026-11-17-checkpoint.md) |
| Stock Sports Displays comparison | Native proxies/notification route traced offline; proposed read-only closed/open comparison not yet performed | [Stock-screen trace](docs/2026-11-20-sports-displays-requests.md) |

## Next focused work

1. Larger-body independent review and the [integration assessment](docs/2026-11-25-larger-body-endpoint-assessment.md)
   are complete. The [separate body/reader/logging preparation](docs/2026-11-25-larger-body-preparation.md)
   passes 36 cloud host checks after a [fortified read-hook correction](docs/2026-11-25-larger-body-host-test-fix.md).
   The corrected owner run passed and both [586-byte ELFs passed static review](docs/2026-11-25-larger-body-build-review.md).
   The owner then passed RAM read-backs, help startup and the [native 586-byte dummy run](docs/2026-11-26-larger-body-vehicle-results.md), including complete trace assessment.
   The separate [open-handle expiry proposal has been reviewed](docs/2026-11-26-open-handle-expiry-assessment.md):
   reuse the endpoint with a new raw-descriptor reader, confirmed-exit release,
   bounded phases and explicit capture/readiness controls. A [separate reader preparation](docs/2026-11-26-open-handle-reader-preparation.md)
   passed all 22 owner host checks and its [QNX build/SDK review](docs/2026-11-26-open-handle-reader-build-review.md)
   now passes: 32 required functions available and 58 compiled sites checked.
   The reader has not run on QNX. The [offline assessor contribution](docs/2026-11-26-held-expiry-assessor-review.md)
   now passes 50 synthetic tests after numeric hardening and proposed
   pre-release trace-gate/cleanup-order amendments. Next implement/test the
   controller, including bounded IO/cleanup and whole-trial watchdog coverage,
   before any vehicle-ready package. A [supplied shell prototype was reviewed](docs/2026-11-26-shell-controller-assessment.md):
   its 12 host tests pass, but independent invalid-control, blocked-output and
   NUL-loss cases expose blockers, alongside missing target printf and PID
   ownership gaps. It is not adopted. A [subsequent C supervisor review](docs/2026-11-26-c-supervisor-assessment.md)
   finds the intended raw-capture/pre-release improvements, but reproduces
   clock-error, late-write and waitpid-ownership defects; guardian identity
   needed resolution. Those r1 results were 5 passed/15 namespace skips.
   [Revision 2 plus local clock/signal fixes](docs/2026-11-26-supervisor-r2-preparation.md)
   now passes 34 host checks with 16 namespace skips and has a frozen Ubuntu
   offline build preparation. The owner then passed all 50 checks with no skips,
   and [QNX ELF/SDK/76-site compiled review](docs/2026-11-26-supervisor-r2-build-review.md)
   passes. A Chromebook RAM-only bundle and status-preserving capture helper
   (14 host checks) are prepared. Next RAM read-backs/help-only startup, then
   the bounded dummy trial; no new ARM result exists. Larger-body cases
   remain separate work.
   The init-check manifest is **586 bytes**; its UI description is **10951 bytes**
   and is separate. Native open-handle/provider-death behavior remains untested. Do not infer
   a 2048-byte reply cap from the incoming message setting or change it blindly.
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
