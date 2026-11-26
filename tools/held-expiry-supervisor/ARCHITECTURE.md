> Owner-supplied Claude architecture for original revision 2. The body below
> is retained as the upstream design record. Local clock/handler corrections,
> 34 passed/16 skipped results, provenance and the Ubuntu build stage are
> described in [REVIEW.md](REVIEW.md). Reported full namespace runs are external
> evidence. No QNX runtime acceptance is implied.

---

# held-controller-1 launcher + supervisor, revision 2 — architecture and review note

Basis: commit 81872c5 and Codex's review in `docs/2026-11-26-c-supervisor-assessment.md`.
Targets the revision-2 proposed contract. The active assessor, contract, reader and
endpoint are unchanged; the tests check their SHA-256 values first.
**Not run on QNX.** Linux host tests do not establish QNX compatibility. No vehicle instructions are given.

## 1. What changed from revision 1

| Review finding | Revision 2 |
| --- | --- |
| Clock failure produced a negative elapsed and no stop | `read_clock` fails explicitly and sets a sticky `clock_failed`; a backwards clock is also a failure. Every deadline predicate treats failure as expired. Kernel-timer ticks decide independently of clock reads. Startup clock failure refuses before any child in both processes |
| Late write reported success | The output deadline is re-checked after every successful write. A late completion returns failure and exit 3 |
| Unexpected `waitpid` error discarded ownership | Four outcomes: collected, running, lost (ECHILD) and wait error. Only a returned PID or ECHILD ends ownership; a wait error keeps it |
| Guardian check-then-kill on a parent PID | Guardian removed. The hard stop is now the **launcher**, the supervisor's parent, which owns it as an unreaped child; plus a self-addressed SIGKILL timer inside the supervisor |
| Startup not covered by the bound | Launcher arms its hard timer before forking. Supervisor arms its timers before descriptor setup, preflight and all output |
| A pre-call check does not bound a late call | Deadline re-checked after the final capture reads, before release; after cleanup, before `WATCHDOG_CANCELLED`; after each write |

## 2. Processes and PIDs

```
caller shell
 └─ L  launcher   = the process the caller starts (its PID is not in the log)
     └─ S  supervisor = contract controller_pid C; the reader's direct parent
         ├─ P  provider (fork + execv pin)
         └─ R  reader   (fork + execv pin; checks getppid() == C)
```

One executable: `--trial` runs the launcher, which forks the supervisor without exec.
The BEGIN record's `controller_pid` is S, and the reader is started with C = S. The
launcher writes nothing to stdout; the log is entirely S's.

## 3. Ownership (both processes, same code)

A child is *owned* from fork until `waitpid(pid, …, WNOHANG)` resolves it.
Signals go only through `signal_owned()`, which refuses once ownership has ended.
That function holds the only `kill()` call in the source, and there is no `wait()` or `waitpid(-1)`.
`SIGCHLD` is explicitly `SIG_DFL` without `SA_NOCLDWAIT`, so an exited child stays a zombie with
its PID reserved until its own parent collects it.

| `waitpid` result | Outcome | Ownership | Signalable | Fixture cleanup |
| --- | --- | --- | --- | --- |
| 0 | running | kept | yes | — |
| that PID | collected, status decoded (exit code or 128+signal) | ended | never again | allowed |
| -1, EINTR | retried, at most 64 times; then a wait error | kept | yes | — |
| -1, ECHILD | **lost**: no status, PID no longer reserved for us | ended | never again | **refused** |
| anything else | wait error, counted | kept | yes | refused while owned |

In the supervisor a lost child records `ABORT child_status_lost` and a wait error
`ABORT child_wait_error`. The abort path still SIGKILLs every owned child and polls
for a bounded number of iterations; anything left uncollected or lost keeps the fixture.

## 4. Deadlines and clock failure

| Bound | S | L |
| --- | --- | --- |
| Trial | 25 s: clock check, **or** first tick of a kernel timer (SIGALRM, then every 100 ms, overruns counted with `timer_getoverrun`) | — |
| Output | 28 s: clock, or tick count > 30 | — |
| Hard | self-addressed **SIGKILL** timer at 31 s (no PID, no clock read) | kernel timer at 30 s, then SIGKILL to owned S; gives up 2 s later (exit 125) |
| Polls | READY 3 s, HELD 3 s, forced reap 100 iterations × 20 ms (iteration-counted) | 20 ms polls; ends on tick counts only |

Clock failure, explicitly:
- **Startup.** Both processes read the monotonic clock once before doing anything else, and
  refuse with exit 2 (`monotonic clock unavailable at startup`) before any fork.
- **Trial.** A failed or backwards read makes `trial_expired()` true, and `stopped()` records
  `ABORT clock_failure`.
- **Cleanup.** Forced collection is iteration-counted, so it ends without the clock.
  `WATCHDOG_CANCELLED` is replaced by `ABORT clock_failure`.
- **Output.** The write is still attempted, so diagnostics can reach the caller, bounded by
  ticks and both hard stops. The exit status is then nonzero (1, or 3 if the failure appeared
  only after END).
- **Launcher.** Its deadlines never use clock reads, only kernel ticks, so a clock failure
  after startup does not weaken it.

A timer handler sets a counter, but the bound does not depend on any loop reading that
counter. Repeated delivery interrupts blocking calls (no `SA_RESTART`); the launcher's
SIGKILL ends S regardless of what S is doing; and S's own SIGKILL timer ends S even if
the launcher is gone.

## 5. Release ordering

Release requires all of the following:

1. The exact HELD prefix, empty reader stderr, and the reader still owned.
2. The provider collected with status 0.
3. The endpoint absent and the alias dangling.
4. The complete control trace (contract §4) and empty provider stderr, checked on raw bytes;
   then a deadline check; then `CONTROL_TRACE_OK`.
5. A final gate: a deadline check, the reader still owned, a fresh read of the reader
   captures, **another deadline check after those reads**, then `kill(R, SIGUSR1)` through `signal_owned`.

The window between that last check and the signal is a few instructions.

## 6. Exit status and acceptance

| Launcher exit | Meaning |
| --- | --- |
| 0 | protocol complete, output complete and on time (the only acceptable value) |
| 1 | ABORT or WATCHDOG_FIRED recorded |
| 2 | refused to start; no provider or reader started |
| 3 | log incomplete, late, or its timing unverifiable (clock) |
| 122 | S collected, but the launcher saw wait errors |
| 123 | launcher hard stop SIGKILLed S |
| 124 | ECHILD for S; S never signalled afterwards |
| 125 | S still uncollected after the hard-stop bound; the launcher exits, relinquishing it |
| 128+n | S terminated by signal n, not by the launcher |

A late or interrupted write can still leave a complete-looking log on disk, and a killed
launcher leaves S to finish on its own. `gate_trial.py` therefore takes the observed launcher
exit status as mandatory input and returns ACCEPT only for exit 0 **and** an assessor PASS.
It loads the unchanged active assessor by path after checking its SHA-256.

## 7. External signals and death

| Event | Behaviour |
| --- | --- |
| HUP/INT/TERM to L | Handler sets a flag; the poll loop forwards the same signal to S while S is owned. Never to P or R |
| HUP/INT/TERM to S | Flag, no `SA_RESTART`; the abort path SIGKILLs and collects S's owned children, frames captures and cleans the fixture |
| Terminal Ctrl-C | The whole foreground group gets SIGINT; L also forwards. P exits through its own handler, R dies; S collects both and reports them |
| S dies | L collects it and exits 128+n. P and R are not signalled by anyone: P detaches at its own lease, R ends at its own hold alarm or probe alarms. The fixture is kept; the log is lost |
| L dies | S continues as usual, and its log still reaches stdout. S's own 31 s SIGKILL timer replaces L's hard stop. The caller sees L's death (e.g. -9), so the gate rejects even a PASS log |
| L's hard stop at 30 s | SIGKILL to owned S only; then as for "S dies"; exit 123 |

Nothing signals a process it does not currently own: L owns only S, and S owns only P and R.

## 8. Tests (all SYNTHETIC; see README for commands)

| Suite | Needs | Tests | Result here |
| --- | --- | --- | --- |
| `test_faults.py` (fault unit, launcher processes, gate) | nothing special | 25 | 25 passed |
| `test_supervisor.py` static and integrity checks | nothing special | 5 | 5 passed |
| `test_supervisor.py` end-to-end (namespace + chroot) | root or user+mount namespaces | 16 | 16 passed; **16 skipped** when `unshare` is hidden from PATH |

With namespaces, 46 tests ran and passed; without them, 30 ran and passed and 16 were skipped.
Both suites passed three further repeated runs together, and leave no processes behind.

- **Fault unit** (`test_support/fault_unit.c`): includes the unchanged source with clock,
  wait, write, kill, pread and fork wrapped, and unit timings shortened (unit build only;
  refuses `__QNX__`). It covers: clock failing mid-trial, going backwards, stuck while ticks
  advance, failing during forced collection and during cleanup, and failing after a complete
  log; late and partial-late writes against an on-time write; ECHILD, EIO, repeated EINTR and
  endless EINTR; and the deadline passing during the final pre-release read.
- **Launcher processes**: exit codes 0/1/2/3/139 propagate; the hard stop sends exactly one
  SIGKILL to the owned child; launcher ECHILD sends nothing; persistent EIO keeps ownership
  and still stops the child (125); transient EIO gives 122; forwarded TERM, HUP and INT reach
  the supervisor stand-in but never its grandchild; an externally killed supervisor gives 137;
  launcher death leaves a self-killing supervisor that ends within 1.5 s.
- **End-to-end** (namespace): the scenario table of revision 1, plus a killed launcher
  (assessor PASS, gate REJECT), a killed supervisor (137; children self-bounded) and the
  launcher hard stop (123).

These tests do not show QNX behaviour of any of the APIs below. The provider is a stand-in
and the post-release read failures are injected.

## 9. QNX SDK/build review items

New since revision 1: `timer_create` with **SIGKILL** as `sigev_signo` (accepted on Linux; QNX
unknown), `timer_getoverrun` in a handler, `timer_delete`, and the second timer per process.
Still open: the `sigevent` layout (`SIGEV_SIGNAL_INIT`?); `fork` without exec in the launcher
and `fork`+`execv` in the supervisor; `waitpid` WNOHANG errno set and zombie retention;
`sigaction` with `sa_flags=0`; EINTR from resource-manager calls; `pread`, `symlink`, `rmdir`,
`opendir`/`readdir`, `fcntl(FD_CLOEXEC)`. The compiled import list, relocations and disassembly
still need review. Codex's export spot check found all 20 earlier functions in the captured libc.

## 10. Residuals

- If the launcher dies, the hard bound becomes S's own 31 s SIGKILL timer, which is unverified on QNX.
- Under clock failure, output timing rests on tick counts and the hard stops. The exit status stays nonzero.
- A release may occur up to a few instructions after the last deadline check.
- If an S that ignores SIGKILL can't be collected, the launcher exits 125, and S becomes the system's to reap.
