# BMW-NBT-Evo-Project
Build inbuilt telemetry data in existing head unit

Build a native iDrive dashboard for the BMW M140i that displays live B58 telemetry directly on the NBT Evo. The goal is everyday operation without a laptop, Bluetooth dongle, or ENET adapter.

## Current status

- QNX shell access over SSH and Python communication with the NBT Evo diagnostic service have been demonstrated.
- The B58 telemetry bridge passed offline tests. Live engine RPM through BMW's Car Data Service (CDS) is still unverified.

## Development setup

- **Ubuntu VM on the Windows PC** builds the dashboard prototype with C++17, SDL2, SDL2_ttf, `g++`, Make, and `pkg-config`.
- **NBT Evo** is the native target. The integration prototype uses C++11, QNX `qcc`, BMW RHMI for the screen, and CDS for vehicle data.
- **Windows laptop** holds the Python ENET diagnostic scripts. The Chromebook was used for the initial SSH access through Bavarian.

## Next milestone

1. Log updates from the candidate CDS property `engine.RPMSpeed` on the head unit with the car stationary and compare them with the instrument cluster.
2. If RPM is verified, display it on a simple RHMI screen and test again after a head-unit restart with external adapters disconnected.
3. Check availability of other signals such as oil temperature. Explore Even Realities G2 integration after the native dashboard has a reliable live feed.
