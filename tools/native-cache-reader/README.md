# NBT native cache reader — 19 November 2026

This is a client-side Python 3 tool for the particular vehicle firmware we
inspected. It runs on Chromebook Linux or Ubuntu. It does not run on the BMW.
Mappings-only and cache inspection have now completed on the vehicle. The
engine-speed cache remained invalid in both engine-off and approximately
700-RPM idle tests. The 26 automated tests use offline fixtures. See the
[vehicle checkpoint](../../docs/2026-11-19-native-cache-checkpoint.md).

The first check collects process/library mappings only. The optional cache
reader follows existing objects through the stock HMI plugin registry. It
does not create an interface, subscribe to CDS, issue diagnostic requests,
load a library, write target memory/files, or restart HMI.

The earlier library-load/unload experiments remain paused following the
observed exit faults and NBT restarts. This tool does not repeat them.

## First check: mappings only

In the **BMW SSH console**, obtain the current process ID:

```sh
pidin -n hu-omap ar | grep -i HmiMain3D
```

Use the actual HmiMain3D PID, excluding the grep process. Never reuse a PID
from an earlier connection or before a reboot.

In **Chromebook Linux**, change to the extracted directory and run the command
below, replacing `CURRENT_PID` with that number:

```sh
python3 nbt_native_cache.py --pid CURRENT_PID --output nbt-cache-mappings.json
```

Enter the BMW SSH password when prompted. The tool uses the established SSH
host-key compatibility option and the normal known-hosts verification. It
opens one SSH connection to root@192.168.16.101 and uses the stock `on` command
to reach hu-omap. No access to ChromeOS drives is required.

Without `--read-cache`, there are zero process-memory reads. A completed
report means only that the process identity and all three required library
mappings were found. Share the JSON report for review before the next step.
The output path must not already exist; keep earlier reports and choose a
new filename for each run. A stopped report explains what prevented the check.

## Optional cache observation, after the mapping check

The implementation also has an explicit `--read-cache` option. Do not add it
to the first command. It verifies four small code/header fingerprints, then
walks the existing ICarDataServer cache and obtains up to three samples per
distinct provider. It checks expected vtables, pointer bounds and object
identity and limits both the amount of memory read and the number of reads.
Missing or unexpected state stops the operation; it is never initialized
or repaired by this tool.

The wire protocol invokes stock `dd` to read bounded regions of the selected
process's `/proc/PID/as`. It creates no remote temporary files and installs
no executable. Password entry has a 120-second initial allowance; individual
reads have a 10-second deadline. Closing or interrupting the client does not
send a signal to HmiMain3D.

The exact code/header fingerprints are compared in process memory. The
recorded full-file SHA-256 values identify the source files used for offline
analysis; the tool does not hash the complete loaded images. These small
checks and vtable checks are guards, not complete runtime/ABI verification.

## Meaning of a cache sample

The inspected stock RPM property uses CPxyVehicle::CEngineSpeed2. A raw
unsigned 16-bit value is divided by four to produce integer RPM. The native
CDS JSON already contains scaled RPM; do not divide that JSON value again.

This observer reports `cached_rpm` only when the associated function-block
pointer and valid byte are nonzero, raw is not 65535, and scaled RPM is in
0..9000. The historical `registration_word_nonzero` report label refers to
that pointer at proxy+0x10, not a subscriber count or an active subscription.
Those checks do not establish freshness. Snapshots are read without locking
or suspending HMI and can race with updates despite identity checks.
Every sample therefore reports freshness as unverified. A zero, plausible
idle value, or changing value by itself is not proof of live B58 telemetry.

Live CDS callback delivery, agreement with the instrument cluster, dashboard
display, and operation without an external dongle remain unverified.

## Offline validation

The additional `--inspect-property` flag requires `--read-cache`. It inspects
the existing property map, current bind flags/handlers and function-block
state. It never calls a target lookup or bind function. Results are attached
to each provider and use the existing global read budget and guards.

This added mode completed engine-off and idle vehicle observations: the
inspected provider had no RPM property entry and its function block was
active in both. See the [results](../../docs/2026-11-19-property-state-vehicle-results.md)
and [review](../../docs/2026-11-19-notification-locator-review.md). Each use
requires a fresh PID. Missing entries or clear flags do
not establish binding history. State 2 does not prove transmission, and
snapshot rechecks are best-effort rather than atomic. No activation is
part of this mode.

From this directory on Chromebook Linux or Ubuntu:

```sh
python3 -m unittest discover -s . -p 'test*.py' -v
```

53 tests passed in the development workspace. They cover cache absence,
invalid status, unavailable/incorrect objects, changing object chains,
cycles, limits, process identity, binary framing over real local pipes,
end-of-file and deadlines. They do not connect to the car and do not verify
QNX `on`, `pidin`, or `dd` transport behavior on the vehicle.

The initial vehicle mappings-only attempt stopped before the ready marker.
A separate SSH command successfully checked `dd` and the current HMI PID.
The revised reader retrieves full `pidin mem` output and filters it on the
client, removing the nested remote grep expression. Startup failures now
report their phase, SSH exit status and the last available startup lines.
The cause of the original failure remains unproven. The revised transport
subsequently completed mappings-only and two bounded cache inspections on
the vehicle; neither inspection returned valid RPM.

The package contains client source, tests, offset/fingerprint metadata and
notes only. It contains no BMW firmware or shared-library payloads.
