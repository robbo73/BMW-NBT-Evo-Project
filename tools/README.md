# Source preparation and historical staging helper

## Inert endpoint prototype on Ubuntu

The [fixed-text QNX endpoint prototype](endpoint-rehearsal/README.md) is
prepared for cross-build/review using the captured SDK interfaces. Sixteen
portable policy checks and a separate callback type check pass. The server
has no plugin/HMI operation and has not been run on the vehicle. The build
script creates an ELF review archive without touching milestone-7 or
executing target code; kernel namespace lifetime remains a future test.
The owner has now supplied that cross-build; its
[offline review](../docs/2026-11-23-endpoint-build-review.md) passes against
the captured libc. No native endpoint execution has taken place.

## QNX resource-manager interface capture on Ubuntu

The [include-only SDK capture](resource-api-capture/README.md) obtains the
existing toolchain's declarations/macros for investigating a process-owned
endpoint. It creates no target executable and needs no BMW connection.
No such endpoint is implemented or activated. Preprocessed vendor output
is for private review and is not committed to GitHub.

## Inert RAM lease rehearsal on Ubuntu

The [C-only rehearsal](ram-lease-rehearsal/README.md) prepares a separate
filesystem timeout experiment, with 13 passing Linux fixture checks. The
Ubuntu build script produces a QNX ELF/readelf review archive without
touching milestone-7, connecting to the BMW or executing the ARM output.
It contains no plugin activation or library loading, and guard death remains
an explicit recovery limitation. The owner has now built the QNX output;
its [offline ELF/runtime review](../docs/2026-11-21-ram-lease-build-review.md)
passes against the captured libc. On 23 November the owner completed the
verified RAM transfer, help-only startup and normal deadline/cleanup path.
See the [vehicle results and limits](../docs/2026-11-23-ram-lease-vehicle-results.md).

## Chromebook initialization-check ready bundle

The [initialization-check helper](init-check/README.md) provides offline
verification, hidden staging/read-back and guarded containment for the
separate reviewed lifecycle build. Its default does not contact the car;
there is no activation or restart command. The separately delivered ready
bundle includes the pinned candidate, which is not stored in GitHub.
29 offline filesystem-backed checks pass; vehicle use of this new helper
remains untested. See the [preparation checkpoint](../docs/2026-11-20-init-check-ready-bundle.md).

## Separate native initialization check on Ubuntu

`prepare_init_check.py` verifies the reviewed full RPM source and can create
a separate lifecycle-only source file with `--write-copy`. It never edits
the original. `build_init_check.sh` runs that preparation and builds the
distinct libNbtAadInitCheck.so using the existing QNX Docker image:

```sh
bash /path/to/build_init_check.sh ~/milestone-7
```

It preserves the full source/binary, refuses existing check-output files and
produces ~/nbt-init-check-review.tar.gz. Build and upload that archive for
offline review; no vehicle installation or execution is performed. See the
[initialization review and trial-plan limits](../docs/2026-11-20-initialization-review.md).

## Initial RPM async-get preparation on Ubuntu

`prepare_initial_rpm_get.py` prepares patch 5 against the exact reviewed
17 November `rhmiapp/nbt_aad_app.cpp`. Its default is a check only:

```sh
python3 /path/to/prepare_initial_rpm_get.py ~/milestone-7
```

After matching the source revision, explicit `--apply` preserves a backup
and adds the initial RPM request:

```sh
python3 /path/to/prepare_initial_rpm_get.py ~/milestone-7 --apply
```

Use either this helper or patch 5, once. A revision mismatch stops before
editing; preserve local changes and inspect differences instead of removing
the hash guard. The helper does not build or connect to the BMW. The
[source review](../docs/2026-11-20-initial-get-preparation.md) records the
verified baseline/output hashes and current validation limits. The owner has
since rebuilt it; the [offline build review](../docs/2026-11-20-initial-get-build-review.md)
records the result. It has not been run on the vehicle. Loading remains paused.

## Guarded stream cleanup on Ubuntu

`prepare_stream_cleanup.py` removes the two unused `<iostream>` includes from
the reviewed source revision after patches 1–3. It checks both complete source
hashes and existing backup paths before editing either file, then preserves
backups with suffix `.before-20261117-stream-cleanup`.

**The owner has already run this helper and rebuilt the candidate. Do not run
it again on that source tree.** It performs the same edits as patch 4; choose
one method only when preparing a matching earlier copy.

For a matching source copy that has not received the cleanup:

```sh
python3 /path/to/prepare_stream_cleanup.py ~/milestone-7
```

This is an Ubuntu source helper. It does not build, contact the BMW, install a
plugin or execute target code. A revision mismatch stops before edits; inspect
the difference rather than removing the hash checks. See the
[17 November checkpoint](../docs/2026-11-17-checkpoint.md) for the reviewed
output and unresolved runtime issue. The helper was validated on a separate
matching source copy; the owner then used it successfully on Ubuntu.

## Historical: stage the frozen RPM logging candidate

**Historical helper: vehicle library-loading tests and HMI activation are
currently paused following observed unit restarts.** This helper targets only
the old 15 November archive, not the rebuilt 16 November candidate. See the
[current checkpoint](../docs/2026-11-17-checkpoint.md) before further vehicle work.

Download [stage_rpm_candidate.py](stage_rpm_candidate.py) from GitHub using
**Download raw file**, then move it into **Linux files → bmw-idrive** on the
Chromebook. Run in the standard Chromebook Linux terminal, not the BMW shell:

```sh
python3 ~/bmw-idrive/stage_rpm_candidate.py
```

The default archive is `~/bmw-idrive/nbt-rpm-test-package.tar.gz`. An explicit
archive path can be passed as the sole argument. Keep the vehicle stationary
with adequate sustained power while doing vehicle work.

The helper:

- Requires the exact audited archive and all five expected payload hashes.
- Uses the existing root SSH connection at 192.168.16.101, with the observed
  ssh-rsa host-key option and normal host-key verification intact. It uses no
  embedded password/token. The short-lived multiplexed connection is closed
  on completion or error.
- Runs file operations in the OMAP node's context and verifies the known
  physical ID5 root. It refuses an existing NbtAad target, staging directory
  or symlink, rather than overwriting it.
- Creates only `/var/opt/hmi/data/ID5/.nbt-rpm-stage-09902c834a37`, copies the
  five files with noclobber and reads every file back byte-for-byte.
- Sets the candidate file permissions after transfer checks pass.

It **does not create Plugins, activate the candidate, execute its code, modify
platform libraries or restart HMI**. A failure can leave a partial hidden stage;
stop and inspect the error instead of deleting or replacing files blindly.

Success prints five `VERIFIED:` lines and:

```text
STAGED ONLY: /var/opt/hmi/data/ID5/.nbt-rpm-stage-09902c834a37
```

The helper passed ten local filesystem-backed mock transport checks covering
successful staging, existing paths/symlinks, bad inputs, interrupted transfer
and corrupted read-back. The owner subsequently verified all five file
read-backs on the vehicle. An SSH multiplexing refusal required fresh
connections and repeated password prompts. That candidate was later made
discoverable, was not observed loaded in HMI, and was rolled back to its hidden
stage. The archive itself is not stored in this repository. See the historical
[preflight](../docs/2026-11-15-vehicle-preflight.md)
and [candidate fingerprints](../docs/2026-11-15-checkpoint.md).
