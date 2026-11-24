# Dummy discovery-link rehearsal — 24 November 2026

## Current action: Ubuntu offline verification

No new QNX compilation is needed. This shell rehearsal reuses the exact
13876-byte C-only endpoint binary that passed both normal deadline and
forced-death tests on the BMW. The ready archive includes that existing
binary for later Chromebook storage, alongside the scripts and source tests.
It contains no BMW library, firmware, SDK output or actual plugin payload.
The compiled endpoint does not change and is never executed by these checks.

From the extracted ready directory, run only:

```sh
bash verify_offline.sh
```

This verifies the package hashes, checks shell syntax and runs 13 Linux
shell-control fixtures. No Docker, compiler, pip dependency, BMW connection
or milestone-7 edit is required. Python 3.8+ and ordinary Ubuntu tools suffice.
The repository copy also supports this command, with a source-only checksum
list; the separately packaged list additionally pins the included executable.

## What the later vehicle script would do

`check_discovery_link.sh` defaults to help with no writes. Its two explicit
options are `--deadline` and `--forced-death`. Do not run either on the BMW
until the Ubuntu result has been reviewed and the vehicle instructions are
provided. In particular, this package performs no automatic upload or run.

The proposed target sequence is:

1. Check the physical, non-linked `/ramdisk/mm` root and the existing regular,
   executable `/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e`.
2. Create one fresh mode-700 `.nbt-endpoint-alias.<shell-pid>` RAM directory;
   never reuse an existing path.
3. Start only the known inert endpoint helper, capture its child PID and
   provide a 15-second helper-only overrun fallback.
4. Create `dummy-discovery.txt` as a symlink to that child's PID-specific
   `/dev/nbt_endpoint_rehearsal.<child-pid>` endpoint. Require the alias to
   resolve as a regular file and read the expected fixed text through it.
5. In deadline mode require normal exit 0. In forced-death mode kill only
   that new child and require wait status 137. Require the alias to remain
   a symlink while both its target and its followed lookup are unavailable.
6. Unlink the owned alias, check for ordinary/hidden/unexpected entries and
   use the known available `rm -r` only on the exact, owned empty directory.
   A changed directory, replaced non-link alias or unexpected entry stops
   cleanup and preserves the affected fixture. No wildcard recursive delete
   or missing QNX `rmdir` utility is used.

Exit/signal traps attempt helper termination and fixture cleanup. The shell
ignores SIGPIPE so closing its output does not automatically abandon cleanup.
These traps cannot run after killing the shell with SIGKILL. A dummy dangling
alias could remain in RAM in that case; the helper still has its own ten-second
lease and previously passed its separate forced-death test. Do not concurrently
modify the protected fixture. The script may unlink a changed symlink at its
owned alias name; it never follows that link for deletion. It preserves a
non-link replacement and unexpected directory entries.

## What this does and does not test

The alias filename has no `.manifest` extension, and its parent is outside
all actual Plugins/PluginsCoded roots. No manifest parser, plugin scanner,
HMI process, CDS request or payload participates. The initialization-only
candidate stays hidden. Actual plugin loading and HMI restart trials remain
paused, and live RPM remains unverified.

The Linux fixtures replace fixed target paths with disposable directories
and scale test sleeps. They use ordinary files, not a QNX IPC or ABI model.
One positive forced-death branch fixture explicitly uses an external Python
thread to remove the ordinary file after its writer dies. That validates
shell decision/cleanup logic only; a separate negative fixture verifies that
a surviving ordinary file cannot count as a pass. Tests also cover default/
bad arguments, missing/linked executable, linked root, alias read, wrong text,
missing endpoint, unexpected hidden entry preservation, hangup, closed output
and overrun failure.

The new alias sequence has not run on the vehicle. Even a vehicle pass would
establish only followed dummy-file lookup/read behavior before and after the
helper stops. Real scanner admission, manifest seek/reader compatibility,
open-handle lifetime, resource retention and HMI-fault containment require
separate review. A link's unavailability does not unload an already-loaded
library or prove safe native C++ initialization.
