# Held descriptor reader — source/build stage

This follows the 26 November external proposal and integration assessment.
Only a new reader is implemented at this stage. No helper process is started,
no fixture is created, no signal is sent and no arbitrary path is accepted.
Help/default prints usage before any file read or active signal setup.

## Fixed input and held phase

The sole active mode accepts canonical shell/provider PIDs, 2..2147483647,
with distinct values; the shell PID must equal getppid(). The fixed parent
/ramdisk/mm/.nbt-held-alias-586.<shell-pid> must be a nonlinked directory under
a nonlinked RAM root. Its dummy-body.bin must be a symlink to exactly
/dev/nbt_large_endpoint_586.<provider-pid>. Open is O_RDONLY, and fstat must
report a regular file of 586 bytes. These checks do not eliminate every
concurrent namespace race; only an owned, isolated fixture is intended.

A raw read of 100 bytes must match the generated prefix, including embedded
NULs. Raw lseek(0,SEEK_CUR) must return 100. The existing body sources are
copied byte-for-byte from the tested larger-body tool; the new independent
Python oracle generates the host test file. No FILE stream is used.

SIGUSR1 is blocked before file access and HELD. The reader then uses
sigwaitinfo rather than a handler/sigsuspend loop: a release arriving after
the HELD marker but before the wait remains pending. The reported signal
sender must equal the original parent PID. The release signal stays blocked
until exit; a late second release cannot terminate the result path.
SIGALRM has default disposition and is explicitly unblocked; SIGPIPE is
ignored so write errors become ordinary failures. No signal is sent by this
reader. POSIX API declarations appear in the captured QNX SDK and the proposed
functions are exported by the captured actual libc. Native behavior still
requires compiled/runtime review. This reader has not been run on QNX.

## Bounds and output

Setup has a five-second alarm, hold has an eighteen-second alarm, each probe
and close has a fresh alarm capped at three seconds. Rearming also caps the
remaining time from a 25-second monotonic budget, rounded upwards to whole
seconds (up to one extra second). There is no timer thread. Signal delivery
and interruption of a blocked QNX operation are not established by Linux
tests. The later controller must enforce its own whole-trial deadline and
bounded cleanup; this reader is not itself a complete containment mechanism.

Records are formatted into a fixed 256-byte buffer and emitted through
checked write loops, retrying EINTR and completing partial writes, under the
current phase alarm. Broken output causes failure; blocked output remains
subject to the alarm. All protocol records use stdout; the later capture
must explicitly preserve stderr diagnostics too. No raw body bytes are echoed.

After authorized release, read64_a, seek_start and read64_b each record a
begin marker, syscall result, immediately saved failure errno and monotonic
elapsed milliseconds. All three must fail promptly (less than 3000 ms).
No errno value is hard-coded. Zero, partial or successful read/seek is an
anomaly; later probes stop and close is still attempted under its own bound.
Close return/errno are observational and are not evidence of availability.

Reader exit 0 and its OBSERVED marker mean only that the controls succeeded
and three calls failed under those local conditions. They are deliberately
not a final PASS. The reader cannot establish that the provider exited,
that the parent sent release at the correct time, or that the endpoint trace
matched the control operations. A killed/timed-out reader is never success.

## Required later controller and assessor

No release before a complete, validated HELD record and provider normal exit
have both been observed. Reap the exact owned provider, require exit 0 and
normal deadline trace, check path absence, and validate the control trace
(read requested/count 100; offset 0 to 100; SEEK_CUR at 100) before release.
Then signal only the exact still-owned reader child, collect all probe/close
records and normal reader status, and clean only the owned dummy fixture.
Abnormal provider exit, missing/duplicate/malformed markers or incomplete
trace are failure. A separate 25-second controller watchdog, bounded child
cleanup, PID identity/reaping/cancellation races and output failures all need
review and tests. Do not reuse the old foreground-stdio shell runner.

Holding through a normal detach plus complete process exit is this case's
scope. It does not isolate detach-only behavior, a request already in flight,
forced provider death, native stdio error behavior, larger data, XML parsing,
HMI lifetime or safe plugin execution. New library imports and ABI handling
must be inspected in the actual QNX build before target preparation.

## Host coverage (22 tests)

The host fixture uses ordinary regular files, not a QNX resource manager.
A private source copy changes only fixed paths and alarm durations to one
second for bounded host tests; the distributed target source retains 5/18/3.
Both normal and linker-wrapped binaries compile with fortification enabled
and warnings as errors. Wrappers intercept read and glibc __read_chk, lseek,
close, write and sigwaitinfo; they are never used by a QNX compile command.
Expected post-release errors are injected, not inferred from Linux unlink.

Checks include real regular-file unexpected success, zero/partial reads,
successful seek, failed controls, pending release before wait, missing release,
wrong sender, stalled read/seek/close with preserved last marker, output partial
writes/EINTR/zero/broken pipe/stall, inherited blocked alarm, close failure,
help/invalid PIDs, wrong bytes/lengths, wrong link target, linked parent,
regular alias and dangling alias. Host tests cannot establish QNX signal or
resource-manager behavior, and they do not validate a future controller.

## Review artifacts

The Ubuntu script builds only nbt_hold_reader_586, records ELF header/programs/
dynamic/relocations/full and dynamic symbols/hashes, and includes own source,
tests and output. hold_api.c is separately preprocessed/compiled to expose
actual off_t/ssize_t/siginfo/stat sizes, member offsets and selected function
types without executing ARM. The preprocessed vendor declarations and object
are private review inputs and must not be committed to GitHub.
