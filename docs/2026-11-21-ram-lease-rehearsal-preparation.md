# Inert C-only RAM lease rehearsal — 21 November 2026

The owner is back on Ubuntu after completing hidden staging and the inert
RAM directory cleanup. No additional BMW connection is required for this
step. The initialization-check and full RPM builds remain unchanged.

Prepared [source, tests and an Ubuntu build script](../tools/ram-lease-rehearsal/README.md)
for a filesystem-only deadline rehearsal. It creates no real plugin link,
uses no manifests/payloads, calls no BMW framework APIs and has no activation
operation. A future target rehearsal would be confined to dummy paths under
the observed RAM mount; no target execution instruction is supplied yet.

The C source has passed 13 Linux fixture checks, compiled with GNU C99 and
Wall/Wextra/Werror. Checks exercise deadline and signal cleanup, loss of
client output, path changes, unexpected data, invalid inputs and the explicit
failure when the guard is killed. No QNX cross-build has been performed in
the cloud: the reviewed Docker toolchain is held on the owner's Ubuntu VM.

The preparation archive includes source/checksums and the build script. On
Ubuntu it will rerun host checks and build a distinct QNX ARM executable,
collect readelf/hashes, and produce ~/nbt-ram-lease-review.tar.gz for offline
inspection. It does not mount milestone-7 or execute the output. ELF format,
interpreter, dependencies, imports and startup code must be checked against
the captured target runtime before considering even an inert vehicle run.

This is a bounded step towards evaluating an independent expiry process,
not a completed temporary loader or a promise of recovery. SIGKILL leaves
the dummy link behind, and restarting an unrelated Linux process is not a
test of HMI, QNX or the vehicle watchdog. Existing RAM lifetime and library
resource/finalization uncertainties remain. See the
[volatile-path review](2026-11-21-volatile-path-review.md) for the evidence
and the [trial plan](2026-11-20-init-check-trial-plan.md) for the current pause.

Follow-up: the owner completed the QNX build and uploaded its output. The
[offline build review](2026-11-21-ram-lease-build-review.md) verifies exact
source/binary identities, QNX interpreter/runtime imports and C-only startup.
No target execution has taken place; no further rebuild is needed for those
reviewed bytes.
