# Endpoint idle-timeout correction — 23 November 2026

## Actual vehicle result: failed normal-deadline check

The owner ran the prepared single-console test with the original reviewed
3df7b9161c30 executable and reported:

```text
READY pid=25358453 path=/dev/nbt_endpoint_rehearsal.25358453 bytes=23 lease_ms=10000
dispatch_handler: Connection timed out
ls: No such file or directory (/dev/nbt_endpoint_rehearsal.25358453)
/dev/nbt_endpoint_rehearsal.25358453: No such file or directory
Endpoint server exit: 1
STOP: endpoint test did not complete normally
```

This is a failed test. READY establishes that the setup/attachment calls
returned success, not that a client ever read or statted the live endpoint.
The helper encountered the first idle timeout and exited before the shell's
delayed metadata/read probes. Those probes found no path. There was no
WATCHDOG message in the pasted result and no successful read or ten-second
expiry observation. No plugin/manifest or HMI operation was involved.

## Root cause from the captured libc

The original loop only recognized a receive failure if dispatch_block
returned NULL. In the captured car libc (SHA-256
7d1199d75bd1187dc3e1842fa89320e9eb82d7215ccf4ce251edcf033cf46baf),
the receive helper beginning 0x30338 stores the receive result in context
word 0. After receive returns -1, it checks errno against 0x104 (ETIMEDOUT)
at 0x30418 and returns the existing context for that case. Other failures
can return NULL. This is the non-null/no-message case missing from our code.

The message handler at 0x31040 checks that word at 0x31050 and branches to
0x3120c to return -1 when it is -1, leaving the timeout error in place.
The observed error therefore matches the incorrect invocation sequence.
This is our prototype's receive-loop bug, not a demonstrated failure of
the BMW publisher, CDS, DME or endpoint support.

## Correction and regression checks

The loop now clears errno before blocking, saves the immediate result/error,
retains any returned context, and checks its public receive ID before
dispatching. Negative/no-context timeout and interruption retry. A valid
positive request or zero-ID pulse is processed even if errno is stale;
errno is reset before the handler. Unexpected receive errors and actual
handler failures remain fatal, including a real handler failure reporting
ETIMEDOUT. There is no broad suppression of handler errors.

Twenty-five host checks pass: the prior 16 bounds/readonly policy checks
plus nine real-main-loop checks using host-only API stubs. The new checks
model the exact non-null timeout contract and ensure no handler is invoked
on that state, preserve context on NULL retries, deliver valid messages
after idle periods, and retain error cleanup/default-help behavior. The
stubs neither touch /dev nor register an endpoint and are not QNX headers,
an ABI model, IPC implementation or a kernel emulator.

The original receive loop was also compiled against the same stubs and
reproduced the fatal timeout path; the corrected loop completes the mocked
deadline without invalid dispatch. This isolates the regression while
leaving real QNX timing/reader behavior unverified. The corrected callbacks
still pass the private SDK-declaration syntax check.

## Fresh Ubuntu build, not a vehicle retry

The new source-only package is nbt-endpoint-timeout-fix-prep.tar.gz, with
usage revision timeout-fix-1 and a distinct output
~/nbt-endpoint-timeout-fix-review.tar.gz. It reruns all host checks and
cross-builds using the existing QNX image without editing milestone-7 or
executing ARM code. The old archive/build remain preserved. The historical
check_deadline.sh now refuses execution until an updated target binary is
built/reviewed and a new command is supplied.

The verified source-only preparation archive is 10706 bytes, SHA-256
390cb1d5da72cb7ad9d33de849cebc78e4bb3c63a27519a427874f6add0a4e3d.
Its extracted checksum list and all 25 host checks passed. It contains our
source/test stubs, not SDK vendor output or an ARM executable.

The new ELF, source hashes, real SDK dependencies and absence of all mock
runtime symbols must be inspected before another inert car test. The fix
has not been built for QNX or run on the car yet. No new BMW observation is
needed for that offline step. Actual plugin loading/HMI restarts remain
paused and live RPM is unverified.

Follow-up: the owner has supplied the corrected QNX build. Its
[offline review](2026-11-23-endpoint-timeout-fix-build-review.md) confirms
the receive-ID check and retry branch in the compiled code, unchanged
runtime imports and absence of host stubs. Native behavior remains pending.
