# Chromebook initialization-check preparation

Prepared 20 November 2026. This uses the **initialization-only** build, not
the full RPM build. Its onInit override logs entry and calls the native base
initializer. It makes no CDS subscription/get request and cannot demonstrate
live RPM. See the [binary review](../../docs/2026-11-20-init-check-build-review.md).

The separately supplied `nbt-init-check-ready.tar.gz` contains this helper,
tests, instructions, trial plan and the frozen five-file candidate archive.
GitHub holds source/instructions only; it does not contain the candidate
binary or BMW assets. Python 3 and OpenSSH on Chromebook Linux are sufficient;
no pip packages or Ubuntu rebuild are needed.

## Now: offline verification

Save the ready archive in **Linux files → bmw-idrive**, then run in the
**Chromebook Linux terminal** (`robbo73@penguin`), not the BMW console:

```sh
cd ~/bmw-idrive
tar -xzkf nbt-init-check-ready.tar.gz
cd nbt-init-check-ready
sha256sum -c SHA256SUMS
python3 nbt_init_check.py check-local
```

All checksum lines should say OK, followed by
`Local archive and all five payload hashes verified.` No car connection is
made. Running the helper without a command also performs only this check.
If the extraction directory already exists, preserve it and check its
contents; do not overwrite a previous bundle blindly.

## Later: hidden staging only

After reconnecting with Bavarian and confirming the ordinary SSH connection
works, use the **Chromebook Linux terminal**, in the same extracted folder:

```sh
python3 nbt_init_check.py preflight
python3 nbt_init_check.py stage
python3 nbt_init_check.py verify-stage
python3 nbt_init_check.py rollback-check
```

Run each command separately and inspect its result before continuing. The
first preflight should report `ABSENT`. Staging should print five VERIFIED
lines and `STAGED ONLY`, with a completed JSON report. The subsequent checks
should report the single hidden stage. Stop on an error or unexpected state.
Do not rerun `stage` to repair a partial/existing directory: it refuses to
overwrite. Preserve the report and use `verify-stage` to inspect the files.

SSH uses root@192.168.16.101, the observed ssh-rsa host-key compatibility
option and normal known-host verification. No password is stored. A private,
short-lived control connection is used; if the old SSH server rejects
multiplexed sessions, fresh sessions may request the password repeatedly.
Other open BMW consoles are not closed by this helper.

The helper checks the physical ID5 root and existing Plugins directory,
rejects linked/conflicting trial paths and an active older NbtAad directory,
and creates only:

```text
/var/opt/hmi/data/ID5/.nbt-init-check-stage-9cc395b60a97
```

It copies exactly five pinned files without overwriting, sets the library
and directory to 755 and assets to 644, and reads all five files back
byte-for-byte. Verification also requires executable access to the directory
and library. It does not create Plugins, move anything into Plugins, run a
probe, load a library or restart HMI. The full RPM build and the older
`.nbt-rpm-stage-09902c834a37` are preserved.

Each remote operation creates a new progress report under `~/bmw-idrive/`.
`--report /new/path.json` selects another new path. A failure can leave a
partial hidden stage; the local report records the last attempted phase.
Reports are observations, not an atomic transaction or proof of recovery.
Do not concurrently rename/edit these target directories while using the
helper.

## Prepared containment command

For a separately reviewed future trial, the recovery helper is already
implemented:

```sh
python3 nbt_init_check.py rollback
```

It moves only `Plugins/NbtAadInitCheck` back to the exact hidden stage after
physical-root/path checks. It refuses an existing destination or symlinks;
an already hidden trial is reported without moving it. It does not delete
files, touch NbtAad or restart anything. Both active and hidden directories
existing is a conflict that stops the operation.

`rollback-check` only checks current paths/utilities. It **does not exercise
the move** or establish recovery from a crash. Hiding an active directory
prevents discovery at a later startup; it does not unload an existing
mapping. SSH must still work for this command. An alternative recovery route
if SSH disappears, sustained power, current ID/name conflicts, baseline logs
and a controlled observation/recovery sequence must be resolved before an
activation trial.

The manifest retains `autoStart=yes` and connector ID 210. Exposing it under
Plugins would enable automatic loading. There is **no activation command**
in this helper. Vehicle loading/restarts remain paused; this package makes
the preparation concrete without lifting that pause.

## Offline validation

```sh
python3 -m unittest -v test_init_check.py
```

29 checks execute the actual shell scripts against temporary **Linux**
filesystem fixtures, with synthetic payloads and no SSH. They cover hash and
archive checks, successful hidden staging/modes, old active candidates,
symlinks/missing paths, interrupted transfers, noclobber, corrupted read-back,
verification without mutation, report preservation and guarded/idempotent
rollback. This fixture testing is not end-to-end validation on QNX.

Update, 21 November: the owner subsequently completed preflight, hidden
staging with all five matching read-backs, and rollback-path inspection on
the vehicle. The initialization-check binary has not been executed, and
the new rollback move has not been exercised there. See the
[staging results](../../docs/2026-11-21-init-check-staging-results.md).
