# Initialization-check hidden staging — 21 November 2026

Source: owner-pasted Chromebook helper output. The local JSON reports named
below remain on the Chromebook; their complete contents have not been
uploaded or independently inspected. No direct cloud connection to the car
was used.

## Completed observations

1. The owner previously extracted the ready bundle and verified every
   SHA256SUMS entry plus the inner archive and all five payload hashes.
2. `preflight` reported `Current trial state: ABSENT` and saved
   `~/bmw-idrive/nbt-init-check-preflight-20261121T022439736625Z.json`.
3. `stage` printed all five VERIFIED lines, matching the
   [frozen candidate fingerprints](2026-11-20-init-check-build-review.md),
   followed by:

   ```text
   STAGED ONLY: /var/opt/hmi/data/ID5/.nbt-init-check-stage-9cc395b60a97
   ```

   The library read-back hash was
   `9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d`.
   The helper saved
   `~/bmw-idrive/nbt-init-check-stage-20261121T022535633992Z.json`.
   Its successful completion also passed its target physical-root/path and
   executable-access guards after setting the staged file/directory modes.
   Password prompts recurred between operations; the transfer and complete
   read-backs nevertheless finished successfully.
4. `rollback-check` reported:

   ```text
   Current trial state: HIDDEN
   Path/utility checks passed. No move was performed.
   ```

   It saved
   `~/bmw-idrive/nbt-init-check-rollback-check-20261121T022723713054Z.json`.

Each remote operation ended with `No activation or HMI restart was
requested.` The new helper has now completed preflight, hidden staging with
read-back, and rollback-path inspection on the vehicle. A separate
`verify-stage` rerun and an actual rollback move have not been performed for
this trial. The staging run already verified all five files.

## Interpretation and remaining work

The initialization-only payload is prepared in its hidden directory; this
does not establish discovery, library loading, application creation,
initialization, finalization, screen stability under a new load, or live
RPM. It makes no CDS/RPM request. The helper does not modify the earlier
hidden NbtAad candidate or expose the new trial under Plugins.

The containment helper's path/utility prerequisites passed, but its move
has not been exercised on this vehicle for this trial. A reverse rename
would not unload an existing mapping and still requires working SSH.
Activation remains paused under the
[trial/recovery plan](2026-11-20-init-check-trial-plan.md).

Before reassessing a native-host trial, obtain a fresh HMI identity and
baseline, inspect active manifest ID/name conflicts, preserve any existing
RAM log, and resolve sustained power, controlled observation/recovery and
the response to lost SSH. Do not repeat a standalone loader probe or
activate the full RPM build to validate this staging result.

Follow-up: a fresh PID/library baseline, stable-screen/ignition state and
RAM-mount listing are now recorded in the
[volatile-path investigation](2026-11-21-volatile-path-review.md). It does
not authorize or establish a recovery-safe loading trial.
