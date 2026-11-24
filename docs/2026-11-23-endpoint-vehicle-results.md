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

## First normal-deadline/read check: failed

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
The native runtime observations were subsequently supplied: this first
check failed at dispatch_handler's idle timeout before a successful read.
See the [failure and correction](2026-11-23-endpoint-timeout-correction.md).
Do not rerun the original executable or treat READY as a serving pass.

The [offline review](2026-11-23-endpoint-build-review.md) still applies.
Actual plugin loading/HMI restart trials remain paused; live RPM is
unverified.

## Corrected timeout-fix-1 build: normal test passed

The owner supplied help-only output identifying the new RAM executable
nbt_endpoint_rehearsal_83c6e473829e, revision timeout-fix-1, with exit 0.
The new bundle's local checksums were also pasted and passed. The raw
read-back OK line for this corrected transfer was not pasted; the next
test was explicitly conditional on that copy block having ended in OK.
This distinguishes supplied evidence from the instruction's precondition.

The owner then ran the updated single-console test and returned:

```text
READY pid=4722805 path=/dev/nbt_endpoint_rehearsal.4722805 bytes=23 lease_ms=10000
-r--r--r--  1 root root 23 Nov 23 09:58 /dev/nbt_endpoint_rehearsal.4722805
READ: nbt-endpoint-rehearsal
DETACHED reason=deadline; endpoint server exiting
Endpoint server exit: 0
PASS: fixed text read; endpoint unavailable after exit
```

This verifies regular-file metadata/read-only mode and size, successful
reading of the expected text, reaching the configured monotonic deadline,
successful cleanup calls, normal exit and independent post-exit lookup
failure for this corrected build. Actual elapsed time was not independently
measured. There was no WATCHDOG output; the normal path completed. The
shell's exact text comparison strips trailing newlines, while metadata
reports 23 bytes. It is not a byte-for-byte binary read-back or a manifest
reader test.

No plugin, manifest or HMI call is part of this experiment. No HMI restart
was requested. These stdout results do not independently establish screen
stability or arbitrary failure recovery. The old 3df7b9161c30 build remains
superseded and must not be reused.

## Prepared forced-death check: pending at this checkpoint

[check_forced_death.sh](../tools/endpoint-rehearsal/check_forced_death.sh)
starts a new copy of the same inert helper, captures its child PID and
first verifies the fixed text at the corresponding endpoint. It then sends
SIGKILL only to that child, requires the expected wait status 137, waits
briefly and checks the exact path with new lookups. A fifteen-second
fallback targets only that same child if the read/start sequence overruns;
fallback/failure cannot count as a successful deliberate-death test.

SIGKILL cannot invoke the helper's detach/cleanup code. A lookup failure
after it would therefore test that death case independently from normal
resmgr_detach. It would not prove cleanup of retained client handles,
manifest/resource lifetime, every SSH failure or HMI restart behavior.
The new script has been syntax-checked. Local shell control-flow checks
confirmed rejection of a missing executable and rejection of an ordinary
file that survives SIGKILL of its writer (status 137, REMAINS, no PASS).
These checks do not emulate or establish QNX registration/IPC lifetime.
The forced-death vehicle check had not yet been performed at this checkpoint.

Follow-up: on 24 November a restored, hash-verified copy passed the forced-death
check. See the [completed result](2026-11-24-endpoint-forced-death-results.md)
for the transcript, exact conclusions and remaining integration limits.
