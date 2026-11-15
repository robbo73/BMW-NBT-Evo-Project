# BMW-NBT-Evo-Project
Build inbuilt telemetry data in existing head unit

Build a native iDrive dashboard for the BMW M140i that displays live B58 telemetry directly on the NBT Evo. The goal is everyday operation without a laptop, Bluetooth dongle, or ENET adapter.

## Current status

- QNX shell access over SSH and Python communication with the NBT Evo diagnostic service have been demonstrated.
- The QNX ARM plugin builds with the GCC 4.9.4 Docker toolchain. A parser change removes an import that the copied BMW C++ runtime does not export.
- The RPM callback now reads accepted telemetry and logs validated RPM. The candidate passes static import and packaging checks; Ubuntu host tests complete, including the lifecycle ThreadSanitizer test, with two checks skipped.
- `HmiMain3D` on `hu-omap` contains the native RHMI loader and maps the required framework/runtime libraries. The candidate's required named imports also match copies taken from this car. Vehicle loading of our plugin, live `engine.RPMSpeed` updates, direct DME communication, and an RPM display remain unverified.

See the [15 November checkpoint](docs/2026-11-15-checkpoint.md) for the exact candidate hashes, evidence, limitations, and next vehicle checks. The two source changes are preserved as [reviewable patches](patches/README.md).

The later [vehicle preflight](docs/2026-11-15-vehicle-preflight.md) records the confirmed paths and storage checks. A [staging-only helper](tools/README.md) verifies and copies the frozen candidate outside the plugin-loading directories; it does not activate code or restart iDrive.

## Development setup

- **Ubuntu VM on the Windows PC** holds the modified source in `~/milestone-7`. The native plugin uses C++11 and the `qnx65-armv7-toolchain:4.9` Docker image. Its host test suite uses `make -C tests HOST_CXX=g++-10 check`. The separate desktop prototype uses C++17 and SDL2/SDL2_ttf.
- **NBT Evo** is the native target, using BMW RHMI for the screen and CDS as the candidate telemetry route. The inspected `hu-jacinto` node runs QNX 6.5.0; it is not yet established as the plugin host.
- **Chromebook** provides SSH access after Bavarian activation. Access survives closing Bavarian but needs activation again after the car's shutdown/sleep cycle. **Windows** holds the earlier Python ENET diagnostic scripts and transfers files to Ubuntu.

This repository currently preserves documentation and patches. The complete modified source, Docker image, BMW libraries and candidate package are held separately; this checkout alone cannot reproduce the build.

## Next milestone

1. Stage and read back the audited candidate outside plugin-loading directories. Review remaining admission checks, controlled activation and recovery before loading it. The Ethernet diagnostic server remains distinct from the native HMI loader.
2. With a reviewed deployment and recovery procedure, test native loading and log changing updates from `engine.RPMSpeed` while stationary. Compare validated RPM with the instrument cluster.
3. If RPM is verified, display it on a simple RHMI screen and test again after a head-unit restart with external adapters disconnected.
4. Check other signals, such as oil temperature. Explore Even Realities G2 integration after the native dashboard has a reliable live feed.
