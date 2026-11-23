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

## Remaining tests and limits

The normal timeout result does not verify behavior after an SSH disconnect,
handled signals, guard death, HMI restart or full-node restart. The Linux
SIGKILL fixture is still an explicit failure case: a dead guard leaves its
dummy link. No native plugin activation or live CDS/RPM result follows.

The next prepared inert check is
[check_hangup.sh](../tools/ram-lease-rehearsal/check_hangup.sh). It verifies
sleep/kill utilities before starting the same child, captures that child's
PID with $!, sends only that child SIGHUP after two seconds, waits for its
expected exit code 2, and checks that its exact dummy directory is absent.
It does not close the SSH connection or target any pre-existing process.
Passing it would establish the delivered-SIGHUP path, not the complete
lost-network/SSH failure scenario. The shell sequence was checked locally
against the host build and temporary fixtures before being supplied; it has
not yet been run on the vehicle.

The pause on actual library-load probes and HMI activation/restarts remains.
See the [offline build review](2026-11-21-ram-lease-build-review.md) and
[volatile-path investigation](2026-11-21-volatile-path-review.md).
