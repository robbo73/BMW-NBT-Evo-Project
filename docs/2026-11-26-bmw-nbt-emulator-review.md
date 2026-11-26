# DAviS0d BMW-NBT-Emulator review — 26 November 2026

Reviewed repository: https://github.com/DAviS0d/BMW-NBT-Emulator

Pinned checkout: `08279f65cdb6e5603d1bb8e2037f84c7b72db670` (commit dated
1 November 2026). A separate research checkout was inspected; no source or
binary from it was copied into this project. This is source/file inspection
and two focused host checks, not a Windows boot or live vehicle test.

## Suitability

This is a substantial work-in-progress emulator for the older **NBT Intel/x86**
platform, not the NBT Evo ARM/OMAP platform in this project's car. Its README
identifies firmware HU_NBT 003_009_004, QNX 6.5 x86, QEMU and a Windows ANGLE
renderer. The extracted HmiMain3D used by its static tests is pinned to SHA-256
554b67d4d6317cfb1715d544874fae8ddd2c975be503c9e2514e2dc2f3a0d693.
Our Evo firmware/library fingerprints, offsets and ARM instruction set differ.

The repository reports working original-menu rendering/input and native Sport
gauges with simulated values. It explicitly lists original navigation engine,
telephone, original audio/Bluetooth, real CAN/MOST and Jacinto as unavailable.
Its host OSM navigation surface is distinct from BMW's original map engine.
Phone projection and Bluetooth hardware integrations remain experimental or
unverified according to its integration note. It is not a complete vehicle
or infotainment implementation.

| Proposed use here | Assessment |
| --- | --- |
| Explore the older NBT menu, animations and simulated gauges | Potentially useful on a compatible Windows PC after obtaining required payloads; runtime not verified here |
| Run the existing ARM libNbtAad.so or inert ARM helpers | Not compatible with this x86 guest as built |
| Rebuild own C-only helpers for QNX x86 and inspect generic filesystem behavior | Possible separate future experiment, requiring a suitable toolchain and guest access; not demonstrated by this review and not an ARM ABI validation |
| Validate actual Evo plugin admission, framework ABI or the earlier runtime failure | Not established by this different firmware/runtime environment |
| Prove B58 CDS delivery, DME access or live RPM | No; real vehicle transport is not implemented |

An Evo/ARM emulator remains a closer target for the current project. This
Windows NBT emulator is optional UI/research work, not a substitute for the
current controlled QNX/Evo investigation.

## What its Sport Displays demonstrate

The host vehicle model accepts simulated RPM/throttle and uses an illustrative
torque curve, then derives power from torque times angular speed. It explicitly
disclaims vehicle calibration. This does not explain how the real BMW obtains
RPM, power or torque.

The native-controls session converts the model's power/torque to percentages
of 400 kW / 800 Nm and writes its emulator mailbox. native_sports.c receives
those percentages, finds the pinned x86 sports helper and calls its original
value setter from the checked UI/render-thread context. Thus simulated values
are delivered directly to the native display helper. It does not demonstrate
activation of engine.RPMSpeed, the real MOST notification path or a DME query.
Its fixed hook addresses and x86 trampoline instructions do not transfer to
our ARM head unit. The separation of simulated input and rendering, identity
checks and UI-thread/lifecycle discipline are useful concepts to study.

## Requirements and completeness of a checkout

The declared host is Windows 10/11 x64, Python with Tkinter and Direct3D 11;
Windows Hypervisor Platform is the acceleration option. Documentation also
describes TCG fallback. The supplied Windows executables do not run natively
on the user's M3 Mac or Ubuntu; no VM/nested-virtualization setup was tested.

The inspected ordinary clone contained the QEMU/renderer binaries, shader
cache, firmware reference and extracted HMI artifact, but its critical IFS
images were only Git LFS pointer files:

| Image | Checkout bytes | Declared LFS object bytes |
| --- | --- | --- |
| walthread_keyboard_dma_v2_prio.ifs | 134 | 261873732 |
| walthread_keyboard_dma_v2_native.ifs | 134 | 262041756 |

A usable installation needs the actual large objects, not merely filenames.
This review did not fetch them or verify their remote availability or hashes.
The viewer's shown missing-file check tests existence, not LFS content, so
that check alone does not establish boot readiness. No conclusion that the
repository boots out of the box follows from our clone or unit tests.

## Focused checks performed

Unmodified test/source files were run with Python -B, without booting QEMU,
building the guest, installing packages or connecting to a car:

- Vehicle simulator: six tests passed in 0.009 seconds (model/control behavior).
- Pinned native sports contract: four tests passed in 0.041 seconds using the
  analysis Python's existing Capstone (x86 byte identities, trampoline layout,
  setter percentage bound and channel mapping).

These ten checks do not establish boot success, rendering, native callback
execution, phone hardware integration or broad repository completeness.
No complete test-suite claim is made.

## Licence and recommendation

The project's own code is source-available under **PolyForm Strict 1.0.0**.
Its licence grants permitted noncommercial/personal use while excluding
modification, distribution and new works based on the software. Third-party
components and BMW firmware are separately covered/excluded by its notices.
Do not import or adapt its code into our repository without an appropriate
grant from the owners. This review records findings and source links only.

Keep it as a possible Windows UI demonstration and comparative research
reference. Do not divert the held-descriptor/controller work or treat its
simulated gauges as a resolution of our live-RPM or framework issues.

## Source links at the inspected revision

- [README and declared limits](https://github.com/DAviS0d/BMW-NBT-Emulator/blob/08279f65cdb6e5603d1bb8e2037f84c7b72db670/README.md)
- [Native integration and runtime claims](https://github.com/DAviS0d/BMW-NBT-Emulator/blob/08279f65cdb6e5603d1bb8e2037f84c7b72db670/docs/NATIVE_INTEGRATION.md)
- [Simulated vehicle model](https://github.com/DAviS0d/BMW-NBT-Emulator/blob/08279f65cdb6e5603d1bb8e2037f84c7b72db670/work/graphics-port/hmi-runner/vehicle_sim.py)
- [Native sports adapter](https://github.com/DAviS0d/BMW-NBT-Emulator/blob/08279f65cdb6e5603d1bb8e2037f84c7b72db670/work/bridge-v2/guest/native_sports.c)
- [Licence](https://github.com/DAviS0d/BMW-NBT-Emulator/blob/08279f65cdb6e5603d1bb8e2037f84c7b72db670/LICENSE)
