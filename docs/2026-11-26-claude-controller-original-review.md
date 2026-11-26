> Historical external review supplied by the owner from Claude. The original
> text follows verbatim; it is not an accepted target procedure. Codex's
> [subsequent assessment](2026-11-26-shell-controller-assessment.md) records
> independently reproduced blockers. Do not use its suggested integration
> steps to replace the active hardened assessor or package the shell runner.
>
> Original upload SHA-256: `d0d70fcc8f5647cdeff85d8584e71991aad43e52d7d46289f1e4db84d1e23ceb`.

---

# held-controller-1 — offline review note, 26 November 2026

`nbt_held_controller.sh` is the controller for the held-descriptor expiry trial.
It emits the PROPOSED held-expiry-log/1 records and never judges the result;
`assess_held_expiry.py` does that. Built against commit cb4c8c0, with the reader,
endpoint and vehicle files unchanged. **It has not run on QNX.** No vehicle
instructions are given here. If it is accepted, it would go through your usual pin,
package and read-back process, like the earlier runners.

## Sequence

1. Help and default do nothing. `--trial` runs preflight: core dumps off; `sleep`, `ln`,
   `mkdir`, `rm` and `printf` present; RAM root canonical and not a link; both pinned
   executables regular, not links, executable. Any failure prints `STOP:` on stderr,
   exits 2 and emits no records.
2. `BEGIN`, then start the whole-trial watchdog (25 s). Create a fresh owned fixture
   (`mkdir` must succeed).
3. Start the provider in the background, stdout and stderr to separate files in the fixture.
   Poll up to 3 s for its exact, newline-terminated READY line. Require the endpoint to be a regular file.
4. Create the alias. Start the reader as a direct background child (`getppid() == $$`).
   Poll up to 3 s for the exact HELD line.
5. `wait` on the provider. It must have status 0 and its `DETACHED reason=deadline` line.
   The endpoint must be absent and the alias still a link but dangling.
6. Only then `kill -USR1` the reader (shell builtin, so the sender is the controller), then `wait` on it.
7. Cancel the watchdog. Emit the four stream sections with exact byte counts, then clean the
   fixture: the alias, the four capture files, a checked-empty directory and `rm -r`.
8. `END result=complete` (exit 0) or `END result=aborted` (exit 1).
   Exit 0 only means the protocol ran; a PASS comes only from the assessor.

On any failure the controller records one `ABORT reason=…` (or `WATCHDOG_FIRED`). It then
SIGKILLs and reaps any child it has not yet reaped, each wait bounded by a 5 s grace timer.
It still emits the sections and cleans up, unless a child could not be reaped; then the fixture is left for inspection.

## Choices made

- **Pre-release check of DETACHED, not of the whole trace.** This closes part of the
  contract's open question. The controller stays a shell script, and the assessor stays
  authoritative for the two control trace events.
- **Watchdog signals the controller, not a remembered PID.** The timer subshell sends
  USR2 to `$$`; the trap only counts, and POSIX requires a trapped signal to
  interrupt `wait`. Grace timers use ALRM the same way. Killed timer subshells leave
  only an orphaned `sleep` with /dev/null stdio, which can signal nothing.
- **Byte counts in pure shell** (`read -r`, `${#line}`, `LC_ALL=C`), so `wc` is not needed
  (contract A6). A partial last line is neither emitted nor counted, and records `ABORT reason=partial_line_<stream>`.
- **Controller stderr is diagnostics only.** Bash prints "Killed" and "Alarm clock" job notices there.
  The log is the controller's stdout; capture that.

## Host test evidence (`test_controller.py`, 12 tests, each scenario under dash and bash)

The reader is a host build of the unchanged `nbt_hold_reader.c` (paths substituted, alarms
5/18/3 s kept) linked with your existing `test_support/raw_faults.c`, so its parent, link,
control and SIGUSR1-sender checks run for real. The provider is a shell stub with a 3 s
lease and canned trace lines. The watchdog is shortened to 10 s and the grace timer to 3 s.

| Scenario | Controller outcome | Assessor verdict |
| --- | --- | --- |
| normal | complete, exit 0 | PASS |
| provider never READY | ABORT provider_not_ready, no reader | ABORTED |
| provider exit 1 | ABORT provider_abnormal_exit, held reader killed (137) | ABORTED |
| endpoint left behind | ABORT endpoint_present | ABORTED |
| no DETACHED line | ABORT provider_not_detached | ABORTED |
| reader control read fails | ABORT held_not_observed | ABORTED |
| SIGTERM to controller after HELD | ABORT external_signal | ABORTED |
| provider never exits | WATCHDOG_FIRED target=both, after about 10 s | ABORTED (timeout finding present) |
| zero-byte probe read | complete (controller doesn't judge) | UNEXPECTED_PROBE_RESULT |
| probe read hangs | complete; reader's own alarm gives status 142 | TIMEOUT_OR_TERMINATED |
| provider stderr text | complete | PREREQUISITE_FAILED |

No aborted scenario sends a release. In every scenario both shells produce well-formed logs,
finish within the bound, leave no owned child running, and clean the fixture. The suite passed
four repeated runs. Static tests check the shipped constants are the production values,
check syntax in both shells, reject non-POSIX constructs, and confirm help, bad arguments and
preflight failures create nothing.

These tests do not show QNX shell behaviour, QNX signal delivery, resource-manager
semantics or real provider death; post-release failures are injected by `raw_faults`.

## QNX shell assumptions to confirm before any use

The old runner already exercised `command -v`, `ulimit -c 0`, `pwd -P`, `[ -L ]`, `kill -9`/`-15`,
`trap` with numbers, background `&` and `wait` natively. New in this script:

1. `printf` is available (preflight refuses to start if not).
2. Signal names `USR1`, `USR2` and `ALRM` work in `trap` and `kill`.
3. `kill` is a builtin, so `si_pid` is the shell's PID. If it isn't, the reader rejects the
   sender and stops: a safe failure, but a wasted run.
4. A trapped signal interrupts `wait`, and a repeated `wait` returns a remembered status.
5. `read -r`, `IFS=`, `${#var}`, `${var%%…}` and `${var#…}` behave as in POSIX sh.
6. `wait` status is 128+n for signal n (contract A5).

dash and bash are the only shells available here. The car's ksh-derived `sh` was not tested.

## Residual risk: PID reuse

The controller signals only its own children. In the normal path the only signal to a
child is the release. Some shells (bash, and probably the car's ksh-derived sh) reap
background children as soon as they exit, so a PID could in principle be reused before
the script signals it. Two windows remain:

- the reader dies on its own between HELD and release (about 8 s), and its PID is reused before the release;
- on abort paths, a child exits on its own just before the forced kill.

A shell script cannot close either window completely. Closing them would need a small C
supervisor that holds each child's status itself. That is a larger change, so it is left
as a review decision rather than built here.

## Worst-case duration

Normal completion is about the 10 s lease plus a few seconds of polling. The watchdog
fires at 25 s; each forced reap is bounded by 5 s and timer cancellation, so the worst case is about 35 s plus cleanup.
