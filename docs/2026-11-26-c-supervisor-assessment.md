# C supervisor contribution: review changes required — 26 November 2026

The owner supplied held-expiry-supervisor.zip, C source and ARCHITECTURE.md
from Claude. The seven-file archive is 26220 bytes, SHA-256
`df822c5866b0f8d246dcfcb8e1d6a6a9fdc7da532ae5b826003a404f63457829`.
All six payload checksums pass; both loose uploads match their ZIP copies.
The source SHA-256 is
`762223f72603891b3bd34fca2b9d5abf17c46dcbb9ef78e15d3acc79ca101117`.
Original file identities and local results are in the [review evidence](evidence/2026-11-26-c-supervisor-review.json).
The [external architecture](2026-11-26-claude-c-supervisor-architecture.md) is
retained with attribution and a separate original hash.

**Disposition: retain for source revision; do not prepare an Ubuntu QNX build
or vehicle package from this version yet.** The active assessor, contract,
reader and endpoint are unchanged. No QNX or vehicle operation occurred.

## Improvements verified by source inspection

The C version addresses the shell proposal's main structure: SIGCHLD disposition
is explicitly reset, signals to provider/reader go through an owned-child check,
waitpid names exact child PIDs, raw capture buffers preserve NULs, and the full
provider control trace plus empty stderr is checked before CONTROL_TRACE_OK
and reader release. Descriptor access avoids stat of the live provider.
The source uses libc formatting rather than requiring a shell printf utility.
Final output is buffered until after trial/fixture processing, and a repeating
signal timer plus guardian attempt to cover stalled output. These are useful
changes, not new native results or a completed proof of every deadline path.

## Local host verification: five passed, fifteen skipped

The package was placed in a separate private repository layout with exact
copies of the active tools. Its hash checks confirm the active assessor,
revision-2 contract, reader, body and fault sources are the intended inputs.
Host binaries compile with warnings as errors, and help/argument/missing-root,
fixed-path, signal-call/static guard and input-integrity checks pass.

The test runner discovered 20 methods in 0.941 seconds: **5 passed and 15 were
skipped** because this environment cannot create the required root/user+mount
namespace/chroot setup. In particular, normal trial, byte-preservation,
blocked-output, guardian and termination cases were not independently rerun
here. The reported four complete 20-pass runs remain external evidence from
Claude, not a result reproduced by Codex. No test was bypassed to imply a pass.

## Three independently reproduced host fault paths

A [small review unit](evidence/2026-11-26-c-supervisor-fault-probe.c) includes the
exact supplied source with its main renamed. Only its clock_gettime, write and
waitpid calls are replaced in that private host unit. No trial is started,
no production path is read and no process is forked or signalled. These are
injected unit observations, not actual QNX clock, IO or process failures.

### 1. A clock error can disable the deadlines

At lines 78–84, now_ms returns the absolute constant HARD_MS*1000 on failure,
with the comment that this forces every deadline. elapsed then subtracts the
stored monotonic start. That constant is not necessarily later than the start.

With start_ms=123456789000 and injected clock_gettime failure, elapsed returned
**-123426789000**, and stopped returned **0**. The repeated timer flag is not
consulted by stopped. Guardian deadlines also use elapsed, so the same clock
failure invalidates its timing claim.

Required revision: use checked clock reads and explicit failure propagation;
never invent an absolute timestamp. Fail before starting children if initial
clock setup fails. Define the runtime-clock-failure path so it aborts/reaps
under an independently established bound. Add start-time and mid-trial clock
failure regressions, including the guardian/hard-stop path.

### 2. The final write accepts completion after its declared bound

At lines 526–536, write_log checks OUTPUT_MS before write. When a positive
write consumes the remaining buffer, the loop ends without checking the clock
again. With the injected clock at 27999 ms before the call and a successful
write completing at **28100 ms**, write_log returned **0** despite its 28000 ms
output bound. This does not show a real 28-second stall; it isolates the
successful-but-late completion branch missing from the supplied tests.

Required revision: check the clock after positive completion, including the
last write, and account for failure in supervisor/transport status. Do not
claim that a full textual capture alone proves output ended before the bound.
A final complete-looking log may already have been delivered, so document how
the caller's real exit status gates assessment. Also audit deadline/signal
checks after cleanup and after capture reads immediately preceding release;
a pre-call check does not bound a call that completes late.

### 3. Unexpected waitpid errors discard ownership as if reaped

At lines 143–158, every nonzero waitpid result ends ownership and marks the
child reaped. The comment describes ECHILD, but the else branch handles every
negative result other than the retried EINTR.

An injected EIO yielded reap_check=1, owned=0, reaped=1 and lost=1 despite no
child status being collected. Finish then treats owned=0 as sufficient to
skip signalling/reaping and may remove captures/fixture while the child is
still live. This contradicts the exact-status ownership rule.

Required revision: distinguish an actual collected PID, zero, ECHILD, EINTR
and other failures. Unexpected errors must not silently relinquish the child
or permit cleanup as if its status had been collected. Bound retries and
preserve resources on unresolved ownership. Add regressions for non-ECHILD
errors and interrupted/repeated waits.

## Guardian identity and deadline architecture still need resolution

The provider/reader ownership model retains their PID reservation until the
supervisor reaps them. The guardian does not have that ownership over its
parent. Its getppid()==parent test followed by kill(parent,SIGKILL) at lines
238–240 is a check-then-signal sequence: if the supervisor dies and its caller
reaps it between those calls, the guardian has no reservation of that numeric
PID. No reuse event was observed or induced here. The source does not justify
an unconditional assertion that the guardian can never signal a reused PID.

Consider a kernel-owned hard timer addressed to the supervisor's own process
identity, subject to QNX SDK/semantics review, rather than a delayed numeric
parent kill. This is a design option, not a claim that SIGKILL timer delivery
has been verified on the car. Another design is acceptable if it establishes
the same identity and failure bounds. Keep the hard stop independent of any
invalid synthetic elapsed value.

The clock origin is also set after preflight. ensure_standard_descriptors,
preflight metadata operations and stop_message writes precede both timer and
guardian setup. Do not describe those startup/error paths as covered by the
current whole-trial bound. Clarify their handling, and the meaning/timing of
WATCHDOG_CANCELLED while output/hard-stop mechanisms remain armed.

## QNX feasibility spot check

All 20 proposed functions spot-checked are exported by the captured actual
car libc: fork, execv, waitpid, timer_create, timer_settime, timer_delete,
nanosleep, pread, symlink, rmdir, unlink, opendir, readdir, closedir, fcntl,
dup2, getppid, sysconf, kill and _exit. This does not establish their correct
SDK signatures, sigevent layout, timer/signal behavior or the final compiler
import list. A corrected revision needs SDK capture and compiled review.

## Focused next work

Correct the three reproduced paths, resolve guardian identity, and add the
regressions to the host suite. Preserve raw capture and pre-release checking,
the fixed production paths and the unchanged active assessor/contract/reader/
endpoint. Label namespace skips honestly and keep external reported reruns
separate from local results. Then inspect a new source package before the
Ubuntu QNX cross-build and API/ELF review. No BMW test is needed for these
changes. Native held-descriptor behavior and live RPM remain unverified;
plugin/HMI trials remain paused.
