# Reviewed RAM lease rehearsal: Chromebook storage bundle

21 November 2026. This bundle contains the exact QNX ARM executable reviewed
after the Ubuntu build. It is an inert C-only filesystem rehearsal, not an
RPM plugin, a loader or a finished recovery mechanism. Nothing in this
archive automatically connects to or changes the BMW.

## Offline check on Chromebook Linux

Save nbt-ram-lease-ready.tar.gz in Linux files -> bmw-idrive. In the ordinary
Chromebook Linux terminal (robbo73@penguin), run:

```sh
cd ~/bmw-idrive
tar -xzkf nbt-ram-lease-ready.tar.gz
cd nbt-ram-lease-ready
sha256sum -c SHA256SUMS
```

Each line should say OK. If the directory already exists, preserve/check
it instead of overwriting. This sequence only extracts and verifies files
locally; it does not execute the ARM binary. The binary is for QNX ARM, not
Ubuntu or Chromebook Linux. No new QNX build or source patch is needed.

Executable identity: 12820 bytes, SHA-256
12bcd2379450108198d83b1a78611337bca5902ff5728fa55bcdb01450c16238.
Source identity: 6385 bytes, SHA-256
4469f32a84f8be2952fa6cf3a601250dbcdadb409f9c9173f067f0197eb3e227.
BUILD-REVIEW.md and audit.json record the static checks against the captured
car libc. No BMW libraries or plugin payloads are included.

## Later vehicle step, not performed yet

At the next connection, first obtain a fresh context and perform a guarded
RAM transfer/read-back using the pinned hash. Startup can then be checked
with help-only before considering the separate ten-second dummy filesystem
rehearsal. Exact commands will be supplied for the OMAP context; this bundle
contains no transfer/activation script to run automatically.

The target executable defaults to help. Its only active mode would create
and clean up private dummy directories/a directory link under /ramdisk/mm.
It uses libc rmdir(), which is present in the captured library despite the
missing shell utility. It never accesses registered Plugins, HMI, manifests,
the hidden initialization-check stage or the full RPM build. No native
library loading or HMI restart is implemented.

QNX execution and timing/cleanup on the actual unit are unverified. The
host SIGKILL test deliberately confirms that a dead guard leaves its dummy
link behind: this is not a guarantee of recovery after lost SSH, guard death
or a head-unit fault. Existing plugin loading/HMI restart trials remain
paused. This rehearsal cannot retrieve or validate RPM.
