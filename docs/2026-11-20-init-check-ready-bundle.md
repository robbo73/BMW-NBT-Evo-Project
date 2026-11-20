# Initialization-check preparation bundle — 20 November 2026

Prepared at the owner's request so the Chromebook can be ready before the
next car connection. No new Ubuntu build is required and no vehicle was
contacted during this preparation.

The separate ready archive contains the reviewed initialization-only
candidate, client-side Python helper, offline tests, instructions, draft
trial plan and SHA256SUMS. The inner candidate is byte-identical to the
85888-byte archive recorded in the [build review](2026-11-20-init-check-build-review.md):
SHA-256 `a564109d08fdcbd71b232f8ac79fbe20f2e3dcd394017a7308c9c4f7099b8018`.
The binary remains SHA-256
`9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d`.
No full RPM binary or old staging payload was changed.

The [helper and operating instructions](../tools/init-check/README.md)
provide an offline default check, read-only preflight, hidden staging with
five complete read-backs, repeat verification, read-only rollback-path
inspection and a guarded reverse move. There is no promotion, execution or
restart operation. Remote operations preserve local progress reports;
interruption can leave a partial hidden stage and never triggers automatic
cleanup/retry/activation.

29 offline tests pass using synthetic inputs and disposable Linux filesystem
fixtures. An initial failure exposed a shell `set -e`/AND-list guard that
could continue when an older active NbtAad directory existed. Required
conditions now use separate checked statements; the old-active and missing
Plugins refusal cases pass. Successful staging, interrupted transfer,
corruption, path/symlink conflicts, no-overwrite, read-only verification,
report preservation and rollback are covered. Extracted-bundle checks verify
the real candidate archive/payload hashes without making an SSH connection.

This prepares hidden staging and the exact containment helper. It does not
prove native initialization, shutdown stability or recovery after lost SSH.
The [trial plan](2026-11-20-init-check-trial-plan.md) still requires those
operating/recovery decisions before activation. In particular, rollback-path
inspection does not exercise a move; a move does not unload a library. The
manifest's autoStart=yes and connector ID 210 remain unchanged. Library
loading and HMI restarts remain paused. BMW binary/assets are delivered
separately and are not committed to GitHub.
