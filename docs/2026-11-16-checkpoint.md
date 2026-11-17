# Native RPM investigation — 16 November 2026

**Historical checkpoint.** The [17 November update](2026-11-17-checkpoint.md)
records the recovered core, runtime findings and newer source-cleanup build.
The candidate hashes and outstanding tasks below describe the earlier state.

**Vehicle library-loading tests and HMI activation are paused following observed
head-unit restarts. Continue with offline investigation on Ubuntu.**

The objective remains native B58 RPM on iDrive without Bluetooth/ENET equipment
in normal use. Live RPM, direct DME communication and an RPM screen have not
been demonstrated. Even Realities G2 integration remains deferred.

## Vehicle host and earlier candidate

`HmiMain3D` runs on `hu-omap`, not the Jacinto Ethernet diagnostic process.
The final read-only capture corrects the earlier hardware baseline:

| Node | Observed CPU | Total RAM | Role in this investigation |
| --- | --- | ---: | --- |
| hu-jacinto | Cortex-A8, 600 MHz | 256 MB | SSH entry point and separate diagnostic services |
| hu-omap | Two Cortex-A15L cores, 1497 MHz | 4096 MB | HmiMain3D and native plugin target |

Both run QNX 6.5.0 ARM little endian. Observed PIDs are historical and can
repeat after boot; they must not be treated as permanent identifiers.

All five files of the [15 November candidate](2026-11-15-checkpoint.md) were
staged and read back successfully. The owner made that candidate discoverable
under the RW Plugins directory, then performed a controlled reboot. iDrive
returned to its normal screen, but the candidate was not observed mapped in
HMI and its RAM log was absent. The owner confirmed successful rollback to:

```text
/var/opt/hmi/data/ID5/.nbt-rpm-stage-09902c834a37
```

The later rebuilt candidate was tested only in separate temporary probe
processes. It has not been activated in the persistent HMI Plugins directory.

## Dynamic-loader findings and source fixes

A small C executable built with the existing QNX GCC 4.9.4 image starts on
OMAP. It calls `dlopen` with `RTLD_NOW | RTLD_LOCAL` and looks up
`pluginAppInfo`, without creating an application object.

The old candidate failed this test with two concrete diagnostics:

```text
unknown relocation type in libNbtAad.so. Symbol:_ZTISt9exception.
unknown symbol: slogf referenced from libNbtAad.so
dlopen failed: Unresolved symbols
```

Static inspection identifies the rejected relocation as `R_ARM_REL32` in
`.ARM.extab`. Matching symbol names alone did not establish relocation
compatibility. The captured boot `libc.so.3` does not export `slogf`;
`libhmilog.so` also does not supply it. Its provider in the full HMI process
remains unidentified.

[Patch 3](../patches/0003-qnx-loader-compat.patch) makes two local changes:

- Use catch-all handling in `Telemetry::ingestUtf16`, preserving rejection of
  invalid telemetry and the public bridge's existing exception boundary.
- Resolve optional system logging with `dlsym` and call it only when available.
  Existing RAM/USB logging remains.

The rebuilt binary and both uploaded source files were inspected. The sources
exactly match the proposed edits. No further source differences were found.

| Rebuilt artifact | Value |
| --- | --- |
| libNbtAad.so size | 112222 bytes |
| SHA-256 | `ac246b424e39a0ca9904f60ae900c01d68daee2e489496cfbb9464cef4534721` |
| Compiler metadata | GCC 4.9.4 |
| Dynamic relocations | RELATIVE, ABS32, GLOB_DAT, JUMP_SLOT; no REL32 |
| Required imports | 121; removed `_ZTISt9exception` and `slogf`, none added |
| DT_TEXTREL | Removed |
| DT_NEEDED | AppFramework, CoreFramework, libstdc++.so.6, libm.so.2; unchanged |

The earlier formatted out-of-range helper remains absent. `pluginAppInfo` and
the validated RPM log format remain present. These are targeted checks, not a
complete target ABI or lifecycle guarantee.

Host validation of the source edits passed 557 telemetry assertions, 2,000
deterministic malformed/mixed inputs and 500 generated RPM payloads with the
old string ABI and Address/UndefinedBehavior sanitizers. The modified logging
body passed checks with a visible system-log provider and with no provider.
The earlier full Ubuntu test-suite result is preserved in the previous
checkpoint; it was not rerun for this documentation update.

## Target load succeeds; process exit and unit stability fail

Read-back hashes of both temporary test files matched. The rebuilt candidate
then reported:

```text
dlopen succeeded; library constructors ran in this probe.
pluginAppInfo found; no application object was created.
```

The probe subsequently terminated with SIGSEGV in the actual QNX libc
`__free+0x70`. The failing caller and the original cause remain unidentified.
Neither RHMI initialization nor the CDS RPM subscription ran in this probe.

The owner supplied two distinct stock-library controls:

| Control | Load result | Exit result |
| --- | --- | --- |
| Vehicle libstdc++.so.6 alone | Succeeded | Expected missing pluginAppInfo; ordinary exit 1 |
| Vehicle AppFramework.A.so alone | Succeeded | Expected missing pluginAppInfo, then SIGSEGV in __free; exit 139 |

The stock framework reproduces the fault without the RPM plugin. It therefore
needs investigation in the context of the probe, runtime and framework
dependencies; it does not establish that HMI activation is safe.

The complete AppFramework attempt shows the process fault followed by an SSH
connection reset. The owner observes that the NBT Evo restarts around these
tests. A later attempt, after the temporary probe was unavailable, returned
126 without executing it and was also followed by a reset. Keep these events
distinct: an SSH reset alone does not establish the trigger, and the restart
mechanism has not been proven. Do not assert a particular watchdog or
memory-pressure cause.

## Final read-only capture

The owner collected process information, RAM directory listings and system
logs, then supplied the archive for offline review. No further loading test
was needed for this collection.

The dumper process arguments identify these configured destinations:

- OMAP: `/var/dump` (singular), for both inspected dump handlers.
- Jacinto: `/net/hu-omap/fs/sda1/dump/jacinto` and `/var/opt/car/pathology`.

The generic `/var/dumps` lookup was not the configured location. The capture
does not include a crash core or a caller backtrace; it does not prove that
all configured dump directories are empty. An existing dump, if retained,
could provide a backtrace without reproducing the crash.

The captured OMAP log contains watchdog heartbeat misses followed by recovery.
It does not contain the earlier probe SIGSEGV or establish a reset action
caused by that probe. Epoch-looking boot/log timestamps also prevent reliable
alignment to civil time from this file alone.

## Offline next steps and limits

1. Review the C-only probe's dynamic C++ runtime startup/cleanup assumptions,
   toolchain destructor registration and stock framework dependency lifecycle.
2. Use existing crash evidence, including a preserved dump if available later,
   to identify the failing caller. No new vehicle reproduction is requested.
3. Reassess the vehicle execution procedure only after this failure is
   understood. Suppressing normal exit cleanup is not proof of compatibility.
4. After stable native initialization is established, verify genuine changing
   `engine.RPMSpeed` samples against the instrument cluster, then add an RPM UI.

No factory startup or watchdog configuration was modified. Raw vehicle logs,
firmware libraries, the HMI executable, compiled plugins and crash dumps are
held separately from this repository. This checkout records the evidence and
source patches; it cannot reproduce the full build on its own.
