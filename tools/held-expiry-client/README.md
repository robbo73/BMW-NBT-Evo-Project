# Chromebook capture for the inert held-descriptor trial

This helper is distributed inside the frozen nbt-held-expiry-ready folder,
with three hash-pinned own executables, the unchanged assessor/gate and build
audit. It is not runnable from this source directory without that package.
Default/help does nothing. Explicit check-local needs no BMW connection.

In Chromebook Linux, after extracting under ~/bmw-idrive:

```sh
cd ~/bmw-idrive/nbt-held-expiry-ready
python3 -B capture_held_trial.py check-local
```

Later, with SSH open to the stationary car, all native actions run on hu-omap:

```sh
python3 -B capture_held_trial.py copy-ram
python3 -B capture_held_trial.py help-only
```

Copy writes only fixed flat /dev/shmem files. It never overwrites an existing
path; exact existing bytes may be reused only after independent read-back.
A linked target, mismatch or transfer error stops. Password prompts and SSH
diagnostics remain visible; ssh-rsa host-key compatibility and ControlPath=none
match the established connection. No password or key is stored.

Only after all help-only checks pass, the explicit trial action is:

```sh
python3 -B capture_held_trial.py trial
```

Trial rechecks every RAM hash and help-only startup before invoking --trial.
The native supervisor creates only its owned dummy RAM fixture and process-owned
endpoint; no plugin, XML, RPM request, HMI operation or restart is performed.
Engine running is not required. Normal provider expiry is the only case here;
forced provider death is not requested.

## Complete evidence and status handling

The remote OMAP shell runs the fixed launcher, captures its actual $? and
emits one final NBT_HELD_LAUNCHER_EXIT trailer, then exits with that status.
The helper preserves the exact SSH stdout as ssh.stdout.raw, removes only
that validated final trailer into capture.hxc, and stores hashes/result.json.
All other bytes, including invalid NULs, are retained for assessor rejection.
Results use a new local nbt-held-run-* directory beside the ready folder.

ACCEPT requires the unchanged gate's assessor PASS, shell-observed launcher
status 0, SSH/QNET command status 0 and agreement of the two statuses.
Missing/partial/repeated trailers, disagreement, connection loss, timeout or
nonzero exit are REJECT even if a delivered body looks complete. The observed
status is extracted automatically, not supplied manually as 0. These checks
are not capture authentication or a proof of the native timer semantics.
QNET on's status/trailer behavior itself remains to be observed on the car;
a discrepancy is a failed test, not a reason to bypass the gate.

A 90-second client timeout includes authentication/transport, not just native
execution. Timed-out output is retained when available with REJECT metadata.
The raw capture is stdout; child stderr is already framed by the native
supervisor. SSH-side stderr is shown live and is not silently merged into the
contract. Preserve the complete result directory after any anomaly; do not
retry or edit a capture to obtain PASS.

## Verification and limits

Fourteen host tests pass against the real unchanged gate/assessor with synthetic
captures and mocked SSH: status/transport failure, truncation, trailer validity,
forbidden-byte preservation, bounds, no-action default, local pins, RAM reuse/
read-back failures and timed-out evidence retention. No cloud SSH, QNX or ARM
execution is performed. The ready package is also checked in its extracted layout.

The new supervisor/held reader have not run on QNX. Timer/signal/process behavior
remains unverified until the bounded native trial completes. The prior 586-byte
stdio trial is separate evidence. Actual plugin/HMI trials remain paused and live
RPM is unverified. Existing hidden candidates and startup/firmware files are untouched.
