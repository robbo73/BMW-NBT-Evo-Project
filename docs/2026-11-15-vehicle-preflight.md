# Connected-vehicle preflight — 15 November 2026

**Historical preflight.** The [17 November checkpoint](2026-11-17-checkpoint.md)
records the subsequent staging, rollback, loader fix and observed unit restarts.
Vehicle library-loading tests and HMI activation are currently paused; the
activation plan below is superseded.

This supplements the earlier [offline checkpoint](2026-11-15-checkpoint.md).
The candidate has not yet been reported staged, installed, loaded or receiving
live RPM. All findings below are user-supplied vehicle outputs or static
inspection of the files the owner copied from the vehicle.

## Host and actual framework copies

`HmiMain3D` runs on `hu-omap` at `/opt/hmi/bin/zipped/HmiMain3D`. Its observed
PID was 286771; rediscover it after a restart. It maps AppFramework,
CoreFramework, libstdc++ and libsocket. The separate Jacinto Ethernet diagnostic
process is not the RHMI host.

The actual car framework copies differ from the earlier build copies:

| Vehicle file | Bytes | SHA-256 |
| --- | ---: | --- |
| libAppFramework.A.so | 51580 | 057618b81375564f5255308a3c59111dd1e9eb57e43e38b7a858bff04ab41ce5 |
| libCoreFramework.A.so | 95400 | 7c6ad2a7134adf8385435487301c88a192a0e8e3bf1bf5ae5c858eb4f92d8202 |

Vehicle files were read from `/fs/sda0/opt/hmi/ID5/lib` in OMAP's context.
Their embedded build paths identify `NBTevo_ID5_1903_Release`; the earlier
copies identify `NBTevo_ID5_2111_Release`. Exact provenance of the earlier
copies remains unconfirmed. A donor-project source does not establish that
its binary libraries came from this car.

Both pairs have identical visible export-name sets (230 AppFramework,
493 CoreFramework), reported exported types/sizes and import-name sets.
The final candidate's 23 required BMW framework imports match the actual
vehicle copies. Its 38 identified required C++ imports match the already
verified car runtime. These are static symbol checks, not a complete ABI or
runtime-loading guarantee.

## Native loader and directory layout

A read-only copy of HmiMain3D is 58795504 bytes, SHA-256
`027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf`.
Static ARM disassembly traces registration of `/Plugins` and `/PluginsCoded`
under the context's RO and RW path selectors, with a conditional coded-app
check for the coded directories. This is evidence from this car's executable,
not solely the newer donor source. Other admission/initialization rules remain
to be validated. The binary was not executed in the cloud or added to GitHub.

Native filesystem observations:

- `/opt/hmi/data` links to `/opt/hmi/ID5/data`; its `ro` child exists.
- `/var/opt/hmi/data/rw` links to `/var/opt/hmi/data/ID5`.
- Physical RW directory: `/fs/sda1/opt/hmi/data/ID5`.
- Backing filesystem: disk partition `/dev/sda0t178`, qnx6 at `/fs/sda1`.
  The observed free space was 348248 KiB (about 340 MiB).
- A unique scratch-file create/write/read/delete check passed in the RW
  directory. The scratch file was removed; no plugin was installed.
- The checked RO root has PluginsCoded, with SecurityMenu/ActiveSeating.
  The checked regular RO/RW Plugins paths were absent. No NbtAad files were
  found in the inspected physical RO data tree.

The native SecurityMenu manifest uses the same broad App/base-name/Etch
connector/asset structure as the candidate. SecurityMenu uses id200; candidate
uses id210. A literal-number search found no `210` in the searched RO/RW
manifest files. This does not rule out all runtime service ID use.

The named `/var/opt/hmi/data/start_ID5_HMI.cfg` was absent. Disassembly shows
the startup reference checks for and deletes that file if present; interpreting
it as an active configuration-input file was a misleading lead. Do not create
or repair that file based on its absence.

## Access, tools and first-test behavior

- Ignition off did not immediately terminate SSH. This demonstrates continued
  head-unit operation, not persistence through full sleep. Bavarian activation
  was still needed after a previous full sleep/power cycle.
- `on -f hu-omap /bin/sh -c ...` works for native OMAP operations from Jacinto.
- `pidin -h` has no embedded usage, and mem/mapinfo shorten library names.
- The remote shell has no `printf` command; the scratch test used `echo`.
- An XML-angle-bracket grep pattern failed through the find/exec shell route;
  a plain `grep -l 210` manifest search completed without matches.
- No files were found at the checked AA daemon, two AA autostart flags,
  app-disable flag or B58-disable flag paths. Existing configuration was not
  changed. The candidate's daemon autostart depends on those autostart flags.
- The candidate includes capped RAM logging at `/dev/shmem/nbt-aad-app.log`
  when USB logging is inactive, unless disabled by `NBT_RAM_LOG`, and uses
  slogf. Actual log creation is untested until the plugin loads.
- The owner initially reported battery-only power, then started the engine to
  charge it. Keep further vehicle work stationary with adequate sustained power.

## Historical activation plan — superseded

The following records the earlier plan, not current vehicle instructions.
Follow the offline investigation status in the current checkpoint.

Use the [staging-only helper](../tools/README.md) to validate the frozen archive,
copy outside the discovery tree and read all five files back. The Chromebook
archive hash already matches the recorded candidate; helper execution remains
pending. Staging does not create a Plugins directory or execute the payload.

Before activation, recheck state, confirm a controlled reload/recovery route,
and define an exact rollback that moves only this candidate outside the
discovery tree. Such a move prevents later discovery; it does not unload code
already running. The AA daemon's source boot guard is not a general recovery
guarantee for native plugin initialization failures.

Then test native loading and genuine CDS payloads, compare changing validated
RPM with the instrument cluster while stationary, and only afterward add an RPM
screen. Sleep/startup operation without external equipment remains unverified.
