# Inert RAM lease rehearsal: offline preparation

21 November 2026. This is a **C-only filesystem rehearsal**, not a plugin
loader or a finished recovery mechanism. It uses dummy directories and an
empty-directory symlink, never a manifest, payload, HMI process or registered
Plugins path. No activation operation exists. The reviewed initialization
check and full RPM source/binary are unchanged.

The reason for this step is the distinction between restarting HMI and
recreating RAM mounts. RAM placement alone cannot stop repeated discovery
after an HMI-only restart. A separate process with a monotonic deadline is
one part of a possible containment design. This rehearsal makes that narrow
part reviewable without entering the mixed BMW C++ runtime.

## Build on Ubuntu for inspection only

Save the separately supplied `nbt-ram-lease-prep.tar.gz` in your Ubuntu home
directory, then run in the **Ubuntu terminal**, not the BMW console:

```sh
cd ~
tar -xzkf nbt-ram-lease-prep.tar.gz
cd nbt-ram-lease-prep
sha256sum -c SHA256SUMS
bash build_review.sh
```

Run each command only if the preceding one succeeds. The script repeats
the checksums, runs 13 host checks using cc, then cross-compiles with the
existing `qnx65-armv7-toolchain:4.9` image and its QNX ARM GCC C compiler.
It does not mount or edit milestone-7, rebuild either plugin, install
anything or execute the generated ARM binary. It refuses existing output
or a previous review archive. A stopped build leaves its output for review;
do not remove or bypass guards to retry blindly.

The result is `~/nbt-ram-lease-review.tar.gz`, containing the C source, host
test log, target binary, readelf header/program/dynamic-symbol reports and
build hashes. Upload that archive for offline inspection before any vehicle
execution is considered. The expected target interpreter is ldqnx.so.2 and
only the QNX C runtime is intended; the actual build still needs verification.

No pip packages or compiler/toolchain changes are required. The Ubuntu host
needs Python 3, cc, readelf, tar, sha256sum and access to the existing Docker
image. Cloud-host fixtures use Linux cc, not the QNX compiler; a successful
host test does not establish QNX binary compatibility.

## What the source implements

The target build defaults to help only. Its sole active mode, **not yet a
vehicle instruction**, would use the fixed canonical root /ramdisk/mm and a
PID-specific private `.nbt-lease-rehearsal.<pid>` directory. Inside it are
`dummy-target`, `dummy-discovery`, and a symlink named `DummyTrial`. There is
no .manifest or executable payload and the entire structure is outside all
observed registered plugin roots.

It verifies that stat resolves its own directory link, then waits for a
10-second CLOCK_MONOTONIC deadline or a handled HUP/INT/TERM. It first
unlinks the dummy discovery entry if its target is still exactly the one
created, then removes only empty owned directories with libc rmdir(). The
libc function does not depend on the missing QNX shell rmdir utility. It
does not recursively delete anything. A replaced link or nonempty directory
causes a failure that preserves the unexpected state.

The implementation deliberately contains no fork, daemonization, HMI
monitoring, process killing, SSH, dlopen, dlsym, socket API or C++ dependency.
All target work is pending offline ELF review and a separate decision about
an inert vehicle rehearsal. No car connection is needed to build it.

## What the 13 host checks establish

Compile with cc, GNU C99, Wall/Wextra/Werror and the explicit host-only
root/short-lease option. All child processes operate on disposable local
Linux fixtures. The host-only option is absent from the target build.

Checks cover deadline cleanup, a closed output pipe, handled HUP/TERM/INT,
an unrelated local process ending while the timer runs, a missing dummy
target, a changed link, a nonempty target, root symlinks, bad arguments,
default help without writes, and forced guard death. The unrelated process
is not an HMI emulator and establishes no BMW restart behavior.

**The SIGKILL check intentionally confirms that the link remains after the
guard is killed.** Signal handlers cannot solve guard death, kernel failure,
lost power or every SSH failure mode. Hiding/revoking a discovery path also
does not unload an already mapped library or establish resource/finalization
safety. This rehearsal does not authorize a future persistent live trial.
A real containment plan still needs explicit handling of guard death,
resource lifetimes, soft restarts, full-node restart and lost SSH.

Library-load probes and HMI activation/restarts remain paused. Nothing here
obtains live RPM. BMW binaries and QNX build outputs are not committed.
