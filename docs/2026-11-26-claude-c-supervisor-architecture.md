> Original external architecture/review supplied by the owner from Claude.
> Retained verbatim below this header. It is not an accepted build or vehicle
> procedure. See the [Codex assessment](2026-11-26-c-supervisor-assessment.md)
> for independently reproduced error paths and limits on local test coverage.
>
> Original SHA-256: `79db5709656fe7867e7370243b67afda74852bb58c054b1edd8bea9045a6b64d`.

---

# held-controller-1 C supervisor — architecture and review note

Basis: commit 0c9b390. Targets the **revision-2** proposed contract in
`tools/held-expiry-assessor/LOG-CONTRACT.md`. The active assessor, its contract,
the reader and the endpoint are unchanged; their SHA-256 values are checked by the host tests.
This is an offline review build. **It has not run on QNX**, and the Linux host tests do
not establish QNX compatibility. No vehicle instructions are given.

## 1. Process model and ownership

```
caller shell
 └─ S  supervisor (C = getpid())           single-threaded
     ├─ G  guardian   (fork, no exec)      hard stop for S only
     ├─ P  provider   (fork + execv pin)   stdout/stderr -> fixture files
     └─ R  reader     (fork + execv pin)   stdout/stderr -> fixture files, parent = C
```

**Ownership rule.** S may signal a child only while it *owns* it, meaning S started it and
has not yet collected its status with `waitpid(pid, …)`. All signals to children go
through one function, `signal_owned()`, which refuses once ownership has been
relinquished. This holds because of three settings:

- `SIGCHLD` is explicitly set to `SIG_DFL` with no flags, so `SA_NOCLDWAIT` is off and children
  are never auto-reaped. An exited child stays a zombie, and its PID stays reserved, until S
  itself calls `waitpid` for that exact PID. An inherited `SIG_IGN` (auto-reap) is overridden at startup.
- S never calls `wait()` or `waitpid(-1, …)`. Every `waitpid` names one owned PID, with `WNOHANG`.
- When `waitpid` returns the PID, ownership ends at that instruction and the decoded status
  (exit code, or 128+signal per contract A5) is stored. Nothing signals that PID again.

So the release `kill(R, SIGUSR1)` and every abort-path `kill(…, SIGKILL)` target either
a live child or a zombie whose PID the kernel still reserves. Neither can be a reused PID.

## 2. Release ordering (the pre-release gate)

S sends SIGUSR1 only after all of the following have been checked, in order, against raw captured bytes:

1. **HELD.** The reader's stdout is byte-for-byte the five expected lines (two control pairs
   with rc=100 errno=0, then `HELD pid=R parent=C provider=P offset=100`), with nothing
   after them. Its stderr is empty, and the reader is still owned (`waitpid` WNOHANG returns 0).
2. **Provider reaped** by S with status 0.
3. **Endpoint absent.** `lstat(endpoint)` fails with ENOENT. The alias is still a
   symlink whose `readlink` equals the endpoint, and `stat(alias)` fails with ENOENT.
4. **Full control trace.** The complete provider stdout is exactly the five lines of contract
   §4: READY for P, SUMMARY `events=2 dropped=0 overflow=0` with a canonical
   `elapsed_ms ≥ 10000`, READ `requested=100 count=100`, SEEK_CUR at 100 with reply code -1, and
   DETACHED reason=deadline. Provider stderr must be 0 bytes. Any byte outside 0x20–0x7E/LF
   fails the check; nothing is stripped or converted first. Only then is `CONTROL_TRACE_OK` recorded.
5. **Re-check just before the signal:** the reader is still owned, and its stdout and stderr are unchanged.

Any failure records one `ABORT reason=…` and no release. The reader is then killed
(it is still owned) and reaped. S never contacts the live provider: it doesn't `stat`
the endpoint while P runs. Its only endpoint lookups come after P is reaped, when the
path manager answers without the provider.

## 3. Capture

Each child's stdout and stderr go to a regular file that S creates in the owned
fixture with `O_CREAT|O_EXCL` (mode 0600, close-on-exec on S's descriptors). Writes to a regular
file on the RAM disk do not depend on S reading, so a child can never be blocked by
S. S reads with `pread` from offset 0 into a fixed 4096-byte buffer, plus one probe byte for
overflow. Sections carry exactly the bytes read, with `bytes=` equal to that length. Nothing is
normalized: a NUL, CR or non-ASCII byte is framed as-is, which makes the log fail the assessor.
S also checks each capture for frameability (allowed bytes, final LF, no `HXC1 ` line, no line
over 512 bytes, no overflow). An invalid capture records `ABORT reason=capture_invalid`. Before
release, any such defect in provider or reader output is already a gate failure.

## 4. Deadlines

All times are monotonic milliseconds from S's start.

| Bound | Value | Mechanism | What it bounds |
| --- | --- | --- | --- |
| READY / HELD | 3 s each | polling loop | provider readiness, reader hold |
| Trial (soft) | 25 s | polling loop + interrupt timer | everything up to READER_REAPED |
| Forced reap | 2 s | polling loop | SIGKILL'd owned children |
| Output | 28 s | interrupt timer + loop check | log write, including a blocked stdout |
| Hard | 30 s | guardian G sends SIGKILL to S | anything S fails to bound itself |

Three layers, because a flag alone does not unblock anything:

1. **Nothing in the trial path blocks indefinitely.** Child waits are `waitpid(WNOHANG)`
   plus `nanosleep(20 ms)`. Captures are files read with `pread`. S does not touch the live
   provider (§2). The log is built in a fixed 64 KiB memory buffer and written only once, at
   the end. During the trial, S's stdout cannot block it, because S doesn't write to it.
2. **Repeating interrupt timer.** `timer_create(CLOCK_MONOTONIC, SIGEV_SIGNAL=SIGALRM)`
   first expires at the 25 s trial deadline, then every 100 ms. The SIGALRM handler is
   installed *without* `SA_RESTART`. Its flag is not the mechanism: delivery is, because it
   makes a blocked `write`, `nanosleep` or `pread` return `EINTR`. A single alarm can be lost
   to the race between checking the deadline and entering a blocking call; the repetition
   closes that race. After 25 s, every blocking call is interrupted at least every 100 ms,
   and each loop re-checks the clock and moves on: trial into abort path, output phase stops at 28 s.
3. **Guardian hard stop.** G is forked first. It resets signals, ignores HUP/INT/TERM, points
   stdio at /dev/null and closes all other descriptors. It then sleeps in 50 ms slices. If
   `getppid()` is no longer C (S has exited), G exits without signalling anyone. At 30 s, if
   its parent is still C, it sends SIGKILL to C. This covers a call that ignores signals (on
   QNX, for example, a client blocked in a send to a wedged server). G never signals P or R. S
   kills G (an owned, unreaped child) and reaps it only after the output phase. So the hard
   bound covers output too, and cancelling G is the last deliberate act.

**Blocked stdout.** S writes the log in a loop. EINTR before 28 s retries, and at or after
28 s stops, the timer guaranteeing an interruption every 100 ms. EPIPE stops (SIGPIPE ignored).
S then cancels G and exits 3. The log is truncated (no END), so it cannot pass. Children are
already reaped and the fixture already cleaned at that point. If output is somehow
uninterruptible, G ends S at 30 s.

**What the log's `WATCHDOG_CANCELLED` means here.** It is appended after `FIXTURE_CLEANED`
and means the 25 s trial deadline had not fired by the end of cleanup. The output deadline and
guardian stay armed while the log itself is written; they are disarmed after the write. A
complete log, ending in END, can only exist if the write finished in time.

## 5. Abort path and cleanup

After any ABORT or WATCHDOG_FIRED (or an external HUP/INT/TERM → `ABORT reason=external_signal`):

1. SIGKILL each still-owned child, then poll `waitpid` for up to 2 s and record `*_REAPED`.
   A child still unreaped records `ABORT child_unreaped`; cleanup is skipped and the
   fixture kept, because a live child may still be using it.
2. Read the four captures and frame them verbatim.
3. Clean only what S created: `unlink` the alias (it must be a symlink) and the four capture
   files (each must be a regular file per `lstat`). Check the directory now holds no entries
   (`readdir`), then `rmdir` it and check `lstat` reports ENOENT. Any surprise (an extra file, a
   replaced alias) records `ABORT cleanup_failed` and leaves the remainder for inspection.
4. `WATCHDOG_CANCELLED` (if the trial deadline did not fire), `END result=…`, then output.

A trial deadline that fires before any child exists has nothing to name in
`WATCHDOG_FIRED target=`. The active grammar allows only provider|reader|both, so it records
`ABORT reason=deadline_before_children` instead.

## 6. Abnormal supervisor termination

| Event | Effect on children and fixture |
| --- | --- |
| S gets HUP/INT/TERM | Handler (no SA_RESTART) sets a flag; the loop takes the abort path: owned children killed and reaped, captures framed, fixture cleaned |
| Terminal Ctrl-C | SIGINT reaches the whole foreground group: P exits via its own handler (`reason=signal`), R dies (default action), G ignores it; S reaps and reports both |
| S SIGKILLed (by G at 30 s, or externally) | P and R are **not** signalled; they are orphaned and adopted by the system. Each is self-bounded: P detaches at its own 10 s lease; R, if never released, ends at its own hold alarm (18 s), or within its probe alarms if released, inside its 25 s budget. G sees its parent change and exits without signalling. The fixture, captures and alias stay in RAM for inspection. The log is lost (or truncated mid-write), so no PASS is possible |

No process ever signals a child that S has reaped, and no surviving process signals an orphan.

## 7. New QNX APIs and assumptions needing SDK/build review

Not yet used by any reviewed target binary: `fork` (single-threaded), `execv`, `waitpid` with
`WNOHANG` and the `WIF*` macros, `timer_create`/`timer_settime` with `CLOCK_MONOTONIC` and
`SIGEV_SIGNAL` (check the QNX `struct sigevent` layout; `SIGEV_SIGNAL_INIT` may be preferred),
`sigaction` with `sa_flags=0` (confirm no implicit restart), `nanosleep`, `pread`, `symlink`,
`rmdir`, `unlink`, `opendir`/`readdir`, `fcntl(F_SETFD, FD_CLOEXEC)`, `O_EXCL`, `dup2`, `getppid`,
`sysconf(_SC_OPEN_MAX)`. The reader already uses `readlink`, `lstat`, `fstat`, `clock_gettime`,
`sigprocmask` and `write`. Runtime questions:

- Does SIGALRM delivery return EINTR from a `write` to the SSH channel, or to a pty?
- Does SIGCHLD=SIG_DFL keep zombies on QNX exactly as POSIX states?
- Are `stat`/`lstat` of a resmgr path served without the provider once it has exited?
- Is fork/exec acceptable here, or would `spawn` be preferred?
- Is `getppid()` adoption semantics after S dies as expected?

These need the cross-build, import list and disassembly review.

## 8. Host test evidence (`test_supervisor.py`, 20 tests, Linux only)

Each trial runs in a private mount namespace plus chroot in which the production
paths exist, so the supervisor and the real reader are compiled from unchanged
source with **no path or timing substitution**. The only host-test build switch is
`NBT_TEST_UNINTERRUPTIBLE_OUTPUT`, in a separately named binary used once to
exercise the guardian; it fails to compile when `__QNX__` is defined. The provider
is always a stand-in: a regular file holding the real body, canned trace lines and a
3 s lease. The reader is the real `nbt_hold_reader.c` with your existing
`raw_faults.c`, except where a stand-in is needed for behaviour the real reader
cannot produce. Every capture goes through the **unchanged active assessor**, loaded
from the repo. The tests check the SHA-256 of the assessor, contract, reader,
body and fault sources against commit 0c9b390 before running.

| Scenario | Supervisor result | Release | Assessor |
| --- | --- | --- | --- |
| normal | END complete, exit 0 | yes | PASS |
| `requested=101` | ABORT control_trace_invalid; reader SIGKILLed (137) | no | not PASS |
| NUL before READY | ABORT provider_output_unexpected; NUL framed verbatim | no | MALFORMED |
| NUL inside trace | ABORT control_trace_invalid; NUL framed verbatim | no | MALFORMED |
| NUL in reader output after release | ABORT capture_invalid; NUL framed verbatim | yes | MALFORMED |
| provider stderr | ABORT control_trace_invalid | no | not PASS |
| provider exit 1 / no DETACHED / endpoint kept / never READY / exits early | matching ABORT | no | not PASS |
| reader dies during hold (stand-in, status 3) | ABORT reader_exited_early | no | not PASS |
| real reader control read fails (status 1) | ABORT reader_exited_early | no | not PASS |
| reader prints extra line before release | ABORT reader_output_unexpected | no | not PASS |
| provider never exits, real reader | reader's own 18 s hold alarm (142): ABORT reader_exited_early | no | not PASS |
| provider never exits, reader blocks all signals | WATCHDOG_FIRED target=both at 25.2 s | no | not PASS |
| probe stalls (real reader) | reader's own 3 s probe alarm, status 142; END complete | yes | TIMEOUT_OR_TERMINATED |
| reader ignores release | WATCHDOG_FIRED target=reader at 25.2 s; reaped 137 | yes | not PASS |
| zero-byte probe read | END complete | yes | UNEXPECTED_PROBE_RESULT |
| unexpected file in fixture | ABORT cleanup_failed; only the stray entry left | yes | not PASS |
| SIGTERM to supervisor after HELD | ABORT external_signal; children reaped; fixture cleaned | no | not PASS |
| stdout pipe already full | exits by itself at 28.1 s, exit 3, log truncated | yes | not PASS |
| output made uninterruptible (test build) | guardian SIGKILLs it at 30.1 s | yes | not PASS |
| supervisor SIGKILLed after HELD | guardian exits in under 1 s; provider exits at its own lease; reader stays held until its own 18 s alarm; nothing released or signalled; fixture left | no | MALFORMED (empty) |

After every trial except the deliberately killed one, no process of that trial
remains (tracked by a per-trial environment marker, which the guardian also carries)
and the fixture is gone, unless the scenario is about leaving it. The suite passed
four repeated runs in about 33 s each. Some aborted logs are classified CONTRADICTORY
rather than ABORTED; that is the unchanged assessor's ordering check reacting to an
abort path, and it is still never a PASS.

## 9. What this does not show

- Any QNX behaviour. In particular: signal interruption of resmgr calls, zombie
  retention, timer and sigevent semantics, `getppid` after adoption, fork/exec cost,
  and EINTR from cleanup calls while the post-deadline timer repeats every 100 ms
  (that could turn a late cleanup into `cleanup_failed`).
- A real provider death. The stand-in provider is not a resource manager, and the
  post-release read failures come from `raw_faults.c`.
- Behaviour over SSH or a pty. The host tests use pipes.
- Anything about plugins, XML, HMI or live RPM.
