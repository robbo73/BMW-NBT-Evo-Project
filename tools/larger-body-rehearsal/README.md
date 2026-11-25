# Separate larger-body rehearsal: Ubuntu build for inspection

25 November 2026. This is a new C-only experiment after the native 23-byte
endpoint/alias/stdio checks. It serves generated binary dummy data, not XML.
The first QNX build is fixed at **586 bytes**. Larger sizes are covered by
host checks only; they are not native results or additional target builds.
The existing tested source, binaries and candidate stages remain unchanged.

## Ubuntu action

From the extracted nbt-large-body-host-fix-prep directory run:

```sh
bash build_review.sh
```

The script verifies all source hashes, runs 36 host tests, then cross-builds
only two separate executables using the existing qnx65-armv7-toolchain:4.9
image: build-qnx/nbt_large_endpoint_586 and build-qnx/nbt_large_reader_586.
It records ELF metadata/symbols/hashes and creates:

```text
/home/rob/nbt-large-body-host-fix-review.tar.gz
```

Upload that archive for ELF/import/compiled-callback inspection. Do not run
either new ARM executable on the BMW yet. The script executes no ARM code,
contacts no car, edits no milestone-7 file and mounts only this preparation
directory in Docker. Existing output/review paths are refused: preserve a
partial build and share its error rather than bypassing those guards.
Host C compiler, Python 3.8+, readelf and the existing Docker image suffice.
No new dependencies are installed.

## Proposed executable behavior, not yet run on QNX

Both programs default to help with no target IO. The endpoint's only active
option would be --serve. It generates its fixed, compile-time bounded body
before registering one /dev/nbt_large_endpoint_586.<pid> file. The body is
immutable while attached. Mode 0444, write/mutation refusal, the ten-second
lease, 100 ms dispatch timeout and corrected receive-ID handling are retained.
Incoming msg_max_size stays 2048 and nparts_max stays 2; neither is treated
as a proven outgoing byte cap. Read count/status/IOV are derived together.

The new lseek wrapper calls the SDK default and preserves its reply/OCB.
It snapshots request fields before the SDK can overwrite the message union.
Read/seek events use a fixed 64-entry memory log with saturating drop count.
Only after detachment/destruction does it print summary/events and elapsed
monotonic milliseconds. Logging has bounded overhead, not zero overhead;
SIGKILL cannot flush it. Overflow is explicit and must not be mistaken for
a complete trace. No handler performs formatting/log IO.

The reader's only active option would be --read-alias SHELL_PID. It accepts
canonical PIDs from 2 to 2147483647 and constructs only:

```text
/ramdisk/mm/.nbt-large-alias-586.<SHELL_PID>/dummy-body.bin
```

It requires a non-linked parent directory, a symlink alias and followed
regular file of the compiled body size. It checks fopen, both fseeks,
nonnegative/exact ftell, one complete fread item, exact binary bytes and
fclose, under the existing default five-second alarm. Its stack buffer is
sized at build time within the hard 16384-byte body cap. It creates/deletes
no files and signals no other process. It does not parse XML.

A later runner requires separate review after these ELFs are supplied.
No new target staging, alias, runner execution or HMI operation is requested
by this package. The 586-byte length matches the frozen init-check manifest
size only; the contents are unrelated dummy binary data containing NULs.

## Host checks and limits

The 36 checks comprise six body/bounds tests across 12 compiled lengths,
six callback/log tests, nine receive-loop tests and 15 reader/error tests.
See DESIGN.md for exact coverage, private captured-SDK declaration checking
and the distinction between synthetic seek replies and native semantics.
Host binaries are compiled in disposable temporary directories. Fault/stub
sources are never passed to either QNX build command.

The new executables have not been QNX-built in the cloud or run on the car.
Actual read sizes, larger replies, seek semantics, trace formatting/timing,
provider death with an open handle and SDK runtime compatibility require
later review/tests. HMI identity/guard lifetime, real manifest admission and
resource lifetime remain unresolved. Actual plugin loading and HMI
activation/restarts remain paused; live RPM is unverified.

## Host fault-injection correction

The first owner-side run stopped before QNX compilation: the read-failure
and blocked-read tests returned the normal success marker. The same two
failures were reproduced with glibc fortification enabled, where source
fread becomes __fread_chk and bypasses a wrapper for fread alone.
The host wrapper now intercepts both entry points, preserving the real
fortified implementation when no fault is selected. Two forced-fortification
regressions require the fortified hook marker, a failed read and actual
SIGALRM termination. No tests are skipped and hardening is not disabled.

All six target C source/header files are byte-for-byte unchanged from the
original preparation, as are the Docker target compile flags. This archive
extracts into a new folder and writes a new review archive name, preserving
the failed build and host-tests.txt in ~/nbt-large-body-prep/.
