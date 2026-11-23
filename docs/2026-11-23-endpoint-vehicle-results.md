# Inert endpoint: vehicle progress — 23 November 2026

Source: owner-pasted Chromebook/BMW console output. No direct cloud SSH
connection to the car is used. Explicit screen-stability confirmation has
not been supplied alongside these results; do not infer it from stdout.

The owner verified all ready-bundle checksums locally, then transferred
the reviewed executable to the OMAP RAM path:

```text
/dev/shmem/nbt_endpoint_rehearsal_3df7b9161c30
```

The transfer used absent-path/noclobber guards and mode 700. A separate
read-back saved as ~/bmw-idrive/nbt-endpoint-readback.AzCwRj matched the
pinned SHA-256
3df7b9161c30d5195975c37b614d92f0bdbfc23792d88c74691e30e735d7a625.
The executable is 13681 bytes.

With core dumps disabled for the shell, the owner ran help-only on OMAP:

```text
Usage: /dev/shmem/nbt_endpoint_rehearsal_3df7b9161c30 --serve
Inert ten-second read-only endpoint: /dev/nbt_endpoint_rehearsal.<pid>
No plugin, manifest, RPM request, library loading or HMI operation.
Endpoint help exit: 0
```

This demonstrates startup, help output and normal C exit for the exact
executable. It registers no endpoint and is not evidence of IPC/read/expiry
or forced-death behavior. No plugin was loaded or HMI restart requested.

## Next prepared check: not yet performed

[check_deadline.sh](../tools/endpoint-rehearsal/check_deadline.sh) starts only
the fixed helper as its own child, captures that child's PID, waits briefly,
lists and reads the corresponding fixed-text endpoint, waits for server
exit, and checks whether new lookup succeeds. All work uses a single BMW
console. It also starts an independent fifteen-second shell fallback that
can SIGKILL only that helper child if it overruns; a normal result cancels
the fallback. No pre-existing PID or HMI process is targeted.

Fallback sleep stdio is redirected to /dev/null, so cancelling its parent
does not leave an orphan sleep holding the console's output stream open.
The fallback is process control for this inert experiment, not a general
vehicle-recovery guarantee. Force-kill, failed reads, nonzero server exit
or a remaining endpoint are failures of this normal-deadline check.

The shell flow was exercised against disposable local control-flow
fixtures for normal completion, wrong text and overrun. Those fixtures use
ordinary Linux files and do not emulate QNX namespace registration/IPC.
The native runtime observations remain pending.

The [offline review](2026-11-23-endpoint-build-review.md) still applies.
Actual plugin loading/HMI restart trials remain paused; live RPM is
unverified.
