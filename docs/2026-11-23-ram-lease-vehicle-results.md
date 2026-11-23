# Inert RAM rehearsal vehicle results — 23 November 2026

Source: owner-pasted Chromebook and BMW SSH console output. No direct cloud
connection to the car was used. The owner reports Chromebook SSH connected,
ignition on and engine off. Screen stability has not yet been explicitly
confirmed alongside these results; no new HMI PID/uptime observation was
requested or captured by this rehearsal.

## Verified transfer and successful startup

The owner extracted the ready bundle and verified all five checksum entries.
The fixed executable was copied with noclobber to the OMAP flat RAM path:

```text
/dev/shmem/nbt_ram_lease_rehearsal_12bcd2379450
```

The transfer printed RAM_COPY_COMPLETE. A separate SSH read-back was saved
as ~/bmw-idrive/nbt-lease-readback.Ek3vZY and passed the pinned SHA-256 check:
12bcd2379450108198d83b1a78611337bca5902ff5728fa55bcdb01450c16238.
The reviewed executable is 12820 bytes. No existing target file was
overwritten by this transfer procedure.

With core dumps disabled for the child shell, help-only execution printed
the expected usage/inert-purpose text and `Help check exit: 0`. This
demonstrates startup, normal C runtime exit and the default/help path for
this exact C-only executable on OMAP. It does not validate BMW framework
loading, the initialization-check plugin or its finalization.

## Normal deadline path

The owner then invoked --rehearse once, receiving:

```text
READY pid=8724596 base=/ramdisk/mm/.nbt-lease-rehearsal.8724596 lease_ms=10000
REVOKED reason=deadline; dummy fixture removed
RAM rehearsal exit: 0
```

This verifies creation of the private dummy tree/link, its initial stat
resolution, reaching the monotonic deadline, successful link revocation,
empty-directory cleanup and normal exit on this QNX filesystem. The
configured lease is 10000 milliseconds; elapsed time was not independently
measured. No Plugins path, manifest, staged payload or HMI interface was
accessed. The executable has no plugin loading, RPM or restart operation.

## Delivered SIGHUP path

The owner subsequently ran
[check_hangup.sh](../tools/ram-lease-rehearsal/check_hangup.sh). It verifies
sleep/kill utilities before starting the same child, captures that child's
PID with $!, sends only that child SIGHUP after two seconds, waits for its
expected exit code 2, and checks that its exact dummy directory is absent.
It does not close the SSH connection or target any pre-existing process.
The shell sequence was checked locally against the host build and temporary
fixtures before being supplied. The vehicle output was:

```text
READY pid=12865652 base=/ramdisk/mm/.nbt-lease-rehearsal.12865652 lease_ms=10000
REVOKED reason=signal; dummy fixture removed
Hangup rehearsal exit: 2 (expected 2)
PASS: signalled child cleaned up
```

This demonstrates handled-signal cleanup and expected normal C exit code 2
for the explicitly signalled child. The final shell checks also confirmed
that this child's exact dummy directory was absent and not a dangling link.
It does not demonstrate actual SSH-loss behavior or HMI stability.

## Remaining tests and limits

Actual SSH disconnection, guard death, HMI restart and full-node restart
remain untested on the vehicle. The Linux SIGKILL fixture is still an
explicit failure case: a dead guard leaves its dummy link. No native plugin
activation or live CDS/RPM result follows.

One further bounded inert check can use a separate SSH connection with
multiplexing disabled: start the same rehearsal, observe READY, then close
only that test connection using the SSH client's local disconnect escape.
Keep the original console open and inspect for residual dummy fixtures
after the ten-second lease. This would test that particular client-close
path; it would not establish every network-loss or reboot scenario. It has
not yet been performed. No native build/source change is needed for it.

The pause on actual library-load probes and HMI activation/restarts remains.
See the [offline build review](2026-11-21-ram-lease-build-review.md) and
[volatile-path investigation](2026-11-21-volatile-path-review.md).

Follow-up: an additional rehearsal fixture was absent after the owner
stopped the test session, but the exact disconnect/stop sequence is not
established. A native /proc listing also lacked cwd/fd paths. See the
[process-owned endpoint investigation](2026-11-23-process-owned-endpoint-investigation.md)
for those observations and the next Ubuntu-only SDK interface capture.
