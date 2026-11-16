# BMW-NBT-Evo-Project
Build inbuilt telemetry data in existing head unit

Build a native iDrive dashboard for the BMW M140i that displays live B58 telemetry directly on the NBT Evo. The goal is everyday operation without a laptop, Bluetooth dongle, or ENET adapter.

## Current status

**Vehicle library-loading tests and HMI activation are paused following observed head-unit restarts.** Continue with offline investigation on Ubuntu.

- QNX SSH access and external Python identification/VIN requests to the NBT Evo diagnostic service have been demonstrated. Direct DME communication remains unverified.
- The QNX ARM plugin builds with the GCC 4.9.4 Docker image. The latest source fixes remove the unsupported exception relocation and make system logging optional, preserving RAM/USB logging.
- The rebuilt library successfully loads and exposes `pluginAppInfo` in a standalone QNX probe, then the probe crashes during exit. Loading stock `AppFramework` alone reproduces the exit fault without the RPM plugin. The owner observes unit restarts around these tests; the mechanism remains unresolved.
- The revised candidate has not been activated in HMI. The earlier candidate was rolled back to its hidden, disabled stage. HMI initialization, live `engine.RPMSpeed` updates and an RPM display remain unverified.
- Host telemetry checks pass, and the earlier Ubuntu test suite completed including lifecycle ThreadSanitizer, with two checks skipped. These results do not establish stable vehicle execution.

See the [16 November checkpoint](docs/2026-11-16-checkpoint.md) for the current evidence, candidate hash and offline next steps. Source changes are preserved as [reviewable patches](patches/README.md).

The [15 November checkpoint](docs/2026-11-15-checkpoint.md), [vehicle preflight](docs/2026-11-15-vehicle-preflight.md) and [staging-only helper](tools/README.md) are historical records for the earlier candidate. Their vehicle activation plan is superseded by the current pause.

## Development setup

- **Ubuntu VM on the Windows PC** holds the modified source in `~/milestone-7`. The native plugin uses C++11 and the `qnx65-armv7-toolchain:4.9` Docker image. Its host test suite uses `make -C tests HOST_CXX=g++-10 check`. The separate desktop prototype uses C++17 and SDL2/SDL2_ttf.
- **NBT Evo** is the native QNX 6.5.0 ARM target, using BMW RHMI for the screen and CDS as the candidate telemetry route. `HmiMain3D` runs on `hu-omap`: two Cortex-A15 cores, approximately 1.5 GHz, 4 GB RAM. The `hu-jacinto` SSH node has a Cortex-A8 and 256 MB RAM; it is separate from the HMI host.
- **Chromebook** provides SSH access after Bavarian activation. Access survives closing Bavarian but needs activation again after the car's shutdown/sleep cycle. **Windows** holds the earlier Python ENET diagnostic scripts and transfers files to Ubuntu.

This repository currently preserves documentation and patches. The complete modified source, Docker image, BMW libraries and candidate package are held separately; this checkout alone cannot reproduce the build.

## Next milestone

1. Investigate the standalone framework/probe exit fault and associated unit restarts offline. Review toolchain startup/destructor handling and existing crash evidence before planning further vehicle execution.
2. Establish a reviewed HMI initialization and recovery procedure once the current failure is understood.
3. Verify genuine changing `engine.RPMSpeed` payloads against the instrument cluster, then add an RPM screen and validate operation without external adapters.
4. Expand to other signals and Even Realities G2 only after the native RPM feed works reliably.
