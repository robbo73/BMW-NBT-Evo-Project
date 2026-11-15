# Stage the frozen RPM logging candidate

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
and corrupted read-back. Those checks do not prove native SSH/on transfer
behavior; the owner's vehicle result is still pending. The archive itself is
not stored in this repository. See the [preflight](../docs/2026-11-15-vehicle-preflight.md)
and [candidate fingerprints](../docs/2026-11-15-checkpoint.md).
