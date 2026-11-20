# Initialization-check native-host trial: draft — 20 November 2026

This is a review plan, not an activation instruction. No vehicle command
in this plan has been run for the new check. The separate build has passed
[offline review](2026-11-20-init-check-build-review.md); loading is still paused.

## Fixed prospective identity

- Trial name: NbtAadInitCheck, library libNbtAadInitCheck.so.
- Hidden stage: /var/opt/hmi/data/ID5/.nbt-init-check-stage-9cc395b60a97.
- Prospective active directory: /var/opt/hmi/data/ID5/Plugins/NbtAadInitCheck.
- Expected physical data root: /fs/sda1/opt/hmi/data/ID5.
- The older .nbt-rpm-stage-09902c834a37 and full RPM build are controls to
  preserve, not destinations to overwrite or activate during this check.

## Preparation before a trial

1. On the Chromebook, verify the frozen candidate archive and five payload
   hashes against the review. Confirm the chosen SSH route works and the
   vehicle can remain stationary with sustained power for observation and
   recovery. Record the current HMI PID and a stable-screen baseline.
2. Inspect the physical root, proposed hidden/active names and connector ID
   conflicts. Refuse existing paths/symlinks or an ambiguous installation.
3. Copy/read back only the hidden trial stage. Verify all five payloads and
   modes. No Plugins exposure, platform-library replacement or restart is
   part of staging. Preserve any existing app RAM log on the Chromebook.
4. Complete and review an exact guarded reverse-move command for this trial
   using the observed filesystem. Verify that the command's prerequisites
   will hold after a proposed promotion. Decide the recovery response to a
   failed/unstable screen or lost SSH before any activation.
5. Only after those concrete checks, reassess a single native-host trial.
   No persistent full-RPM activation or standalone C loader probe is included.

## Evidence to capture if a trial proceeds later

Look for these stages in order; do not infer one from the preceding stage:

- Fresh HMI identity and a mapping of libNbtAadInitCheck.so.
- The library-loaded banner containing init-check-1.
- create(name=...) and the subsequent created-app marker.
- INIT CHECK: onInit entered.
- INIT CHECK: base onInit returned 1, with the screen remaining stable.

RAM logging uses the existing /dev/shmem/nbt-aad-app.log path. Its presence
depends on the existing logging configuration and file-open success. The
check contains no RPM request, so an invalid RPM cache is not its pass/fail
criterion. Missing markers or a restart require investigation, not repeated
reboots or an immediate switch to the full RPM candidate.

## Rollback semantics

The intended reverse move is from the exact active trial directory back to
the exact hidden stage. A future command must verify the physical ID5 root,
reject linked/mismatched paths, require the active trial directory and
refuse an existing hidden destination before using mv. Idempotent handling
of an already hidden trial must be explicit. It must not delete files or
touch the older NbtAad stage.

That rename prevents discovery at a subsequent startup. It does not unload
an already running library, stop a callback or prove shutdown safety. The
follow-up restart/recovery sequence must be controlled and checked separately.
If SSH is unavailable, the move cannot be relied on; the alternative recovery
route and its limits must be resolved before activation. The earlier
successful rollback is evidence for that file operation, not universal
recovery from any head-unit fault.

Any observed instability ends that trial. Preserve available logs/current
identity and perform the reviewed containment/recovery procedure without
repeating the fault. No firmware keys, factory startup files, watchdog
configuration, coding or platform libraries are to be changed by this trial.
