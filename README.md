# BMW-NBT-Evo-Project
Build inbuilt telemetry data in existing head unit

Build a native iDrive dashboard for the BMW M140i that displays live B58 telemetry directly on the NBT Evo. The goal is everyday operation without a laptop, Bluetooth dongle, or ENET adapter.

## Current status

**Vehicle library-loading tests and HMI activation are paused following observed head-unit restarts.** Continue with offline investigation on Ubuntu.

- QNX SSH access and external Python identification/VIN requests to the NBT Evo diagnostic service have been demonstrated. Direct DME communication remains unverified.
- The QNX ARM plugin builds with the GCC 4.9.4 Docker image. Source fixes remove the unsupported exception relocation, make system logging optional and remove two unused `<iostream>` includes. The 17 November rebuild removes both stream-initialization imports without adding required imports.
- The previous candidate loads and exposes `pluginAppInfo` in a standalone QNX probe, then crashes during exit. Loading stock `AppFramework` alone also faults. An existing probe core now identifies a cross-runtime shutdown path: QNX's stream destructor calls GNU's stream destructor, which passes address `8` to the allocator. Binding/initialization ordering and the associated unit restarts remain unresolved.
- The latest full RPM candidate is **reviewed offline only**: 112212 bytes, SHA-256 `a1e5bd912a24984bac48d420bb711beecce83d87ad6678f7c1c322e46881faf3`. Its initial RPM async-get adds one required import, exported by the actual car's AppFramework, and retains the earlier relocation/stream cleanup. It has not been executed on the car or activated in HMI. The earlier candidate was rolled back to its hidden, disabled stage. HMI initialization, live `engine.RPMSpeed` updates and an RPM display remain unverified. See the [20 November build review](docs/2026-11-20-initial-get-build-review.md).
- A separate 43757-byte initialization-only build passes offline checks: no CDS, callback-posting, action-registration, socket or process-launch imports remain. It preserves the full RPM source/binary and has not been run on the vehicle. See its [build review](docs/2026-11-20-init-check-build-review.md) and [draft trial/recovery plan](docs/2026-11-20-init-check-trial-plan.md).
- The [Chromebook ready bundle](tools/init-check/README.md) provides integrity checks, hidden staging/read-back and guarded containment for that separate build. Its 29 fixture checks pass. On 21 November the owner completed vehicle preflight, all five hidden-stage read-backs and rollback-path inspection; no move, activation or HMI restart was requested. See the [staging results](docs/2026-11-21-init-check-staging-results.md). The vehicle-execution pause remains in place.
- Host telemetry checks pass, and the earlier Ubuntu test suite completed including lifecycle ThreadSanitizer, with two checks skipped. These results do not establish stable vehicle execution.
- The separate fixed-text QNX endpoint prototype passes [offline build review](docs/2026-11-23-endpoint-build-review.md): all 33 required function imports exist in the captured libc and the relevant callback layout checks match. Its verified RAM copy has now passed help-only startup/exit on the car. Endpoint serving/read behavior and lifetime after expiry or forced death remain unverified; see the [vehicle progress](docs/2026-11-23-endpoint-vehicle-results.md). No manifest or plugin is served.
- A separate C-only RAM deadline rehearsal has been cross-built and [reviewed offline](docs/2026-11-21-ram-lease-build-review.md): its only dependency is libc.so.3 and all 28 required function imports are exported by the captured car runtime. On 23 November its verified RAM copy passed help-only startup/exit, normal deadline cleanup and explicit SIGHUP cleanup on QNX. See the [vehicle results](docs/2026-11-23-ram-lease-vehicle-results.md). It uses dummy paths and contains no activation/loading operation. Guard death remains an explicit limitation; this is not yet a live-plugin recovery mechanism.

See the [17 November checkpoint and handover](docs/2026-11-17-checkpoint.md) for the current evidence, candidate fingerprints and where to resume. Source changes are preserved as [reviewable patches](patches/README.md).

The [16 November checkpoint](docs/2026-11-16-checkpoint.md), [15 November checkpoint](docs/2026-11-15-checkpoint.md), [vehicle preflight](docs/2026-11-15-vehicle-preflight.md) and staging-only helper are historical records. Their vehicle activation plans are superseded by the current pause. The [tools guide](tools/README.md) also documents the guarded source-cleanup helper already used on Ubuntu.

## Read-only inspection tool — 19 November

The [native cache reader](tools/native-cache-reader/README.md) is a client-side Python tool for Chromebook Linux or Ubuntu. Static analysis identified the native `engine.RPMSpeed` provider and its raw-to-RPM conversion. Following a startup revision, mappings-only and two bounded cache inspections completed on the vehicle, passing code/header fingerprints and object checks. The existing engine-speed cache remained invalid both with the engine off and at an owner-reported idle of about 700 RPM; live RPM remains unverified. The reader has 89 passing offline tests and installs no target executable, loads no libraries and does not restart HMI. The property/state mode also completed engine-off and idle observations: no RPM entry existed in the inspected provider and its function block was active in both. See the [vehicle results](docs/2026-11-19-property-state-vehicle-results.md). The activation pause remains in effect. See the [19 November checkpoint](docs/2026-11-19-native-cache-checkpoint.md). No BMW binaries are included.

Offline review of the actual vehicle's coding library identifies the separate app-admission predicates. The opt-in observer's first vehicle run completed: both predicates passed in one cached variant-server instance. Its association with the app manager's execution scope remains unverified, and the result does not prove plugin loading. See the [vehicle results](docs/2026-11-20-app-admission-vehicle-results.md) and [coding review and limits](docs/2026-11-19-app-admission-review.md).

The manager-path observer also completed a vehicle run. It confirms the intended RW Plugins root is registered without the per-directory coded-name filter. The older candidate remains hidden; no new plugin was loaded. See the [registered-path results](docs/2026-11-20-plugin-manager-vehicle-results.md).

## Development setup

- **Ubuntu VM on the Windows PC** holds the modified source in `~/milestone-7`. The native plugin uses C++11 and the `qnx65-armv7-toolchain:4.9` Docker image. Its host test suite uses `make -C tests HOST_CXX=g++-10 check`. The separate desktop prototype uses C++17 and SDL2/SDL2_ttf.
- **NBT Evo** is the native QNX 6.5.0 ARM target, using BMW RHMI for the screen and CDS as the candidate telemetry route. `HmiMain3D` runs on `hu-omap`: two Cortex-A15 cores, approximately 1.5 GHz, 4 GB RAM. The `hu-jacinto` SSH node has a Cortex-A8 and 256 MB RAM; it is separate from the HMI host.
- **Chromebook** provides SSH access after Bavarian activation. Access survives closing Bavarian but needs activation again after the car's shutdown/sleep cycle. **Windows** holds the earlier Python ENET diagnostic scripts and transfers files to Ubuntu.

This repository currently preserves documentation and patches. The complete modified source, Docker image, BMW libraries and candidate package are held separately; this checkout alone cannot reproduce the build.

## Next milestone

1. Continue on Ubuntu with the captured core and libraries: investigate the real HMI's runtime binding/initialization context and plugin-discovery behavior. The stream cleanup is verified statically; no further rebuild is needed to validate those two source edits.
2. Establish a reviewed HMI initialization and recovery procedure after assessing the unresolved runtime failure. Do not use another standalone car probe to validate the cleanup.
3. Verify genuine changing `engine.RPMSpeed` payloads against the instrument cluster, then add an RPM screen and validate operation without external adapters.
4. Expand to other signals and Even Realities G2 only after the native RPM feed works reliably.
