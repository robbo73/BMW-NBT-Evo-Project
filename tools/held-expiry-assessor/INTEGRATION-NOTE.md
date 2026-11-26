> Historical external integration note, supplied by the owner from Claude.
> The text below describes the original 45-test proposal. The adopted parser
> has 50 tests and proposal-revision-2 amendments; see [REVIEW.md](REVIEW.md)
> and [LOG-CONTRACT.md](LOG-CONTRACT.md) for current requirements. In particular,
> CONTROL_TRACE_OK is now required before release, and watchdog cancellation
> follows cleanup. Original bytes are fingerprinted in PROVENANCE.json.

---

# Integration note: held-descriptor expiry assessor — 26 November 2026

Built against commit cb4c8c0. No reader, endpoint, package or vehicle file
was changed. Every log in this folder and its tests is **synthetic**.
Nothing here has run on QNX; no live RPM, plugin or HMI conclusion follows.

## Files

| File | Purpose |
| --- | --- |
| `LOG-CONTRACT.md` | **PROPOSED** held-expiry-log/1 controller records, stream framing, assumptions A1–A8 |
| `assess_held_expiry.py` | Offline assessor; stdlib only (argparse, json, pathlib, re, sys); one local file in, JSON out |
| `test_assess_held_expiry.py` | 45 tests on synthetic logs (`python3 -B -m unittest test_assess_held_expiry`) |
| `examples/SYNTHETIC-*.log` | One passing and one zero-byte-read synthetic log, with their assessment output |

Exit code 0 and the final `PASS:` line appear only when there are no findings. Every other
outcome exits 1 with one verdict, the most severe found:
MALFORMED > CONTRADICTORY > ABORTED > TIMEOUT_OR_TERMINATED > UNEXPECTED_PROBE_RESULT >
PREREQUISITE_FAILED > INCOMPLETE. The findings list keeps every reason.

## How the seven requirements map to checks

1. Controls/HELD: reader `CONTROL_END` rc=100 errno=0 for both, the exact HELD line, and the controller's HELD_OBSERVED.
2. Trace: provider stdout is exactly READY, SUMMARY events=2 with no drops, READ 0→100
   requested=100 count=100, SEEK_CUR(1) at 100, DETACHED reason=deadline. Reply code -1
   (A3) is kept as `endpoint_reply_code`, separate from the reader's `syscall_result`.
3. Release gating: RELEASE_SENT must come after HELD_OBSERVED, PROVIDER_REAPED status=0
   and ENDPOINT_ABSENT. This is checked by position, so a reordered log is flagged "premature
   release" rather than only "out of order".
4. Identity: C, P and R are distinct and agree across BEGIN/fixture, READY, alias target,
   READER_STARTED, HELD, RELEASED sender, both REAPED records and FIXTURE_CLEANED.
5. Probes: three OP_END records with rc=-1, errno ≥ 1 and 0 ≤ elapsed < 3000. Errno is recorded
   only. A zero-byte read at offset 100, any bytes, or a successful seek gives UNEXPECTED_PROBE_RESULT.
6. Completion: close OP_END is present (either result is accepted as an observation), reader status 0 with
   OBSERVED, both stderr sections empty, FIXTURE_CLEANED and END result=complete.
7. Integrity: gapless seq, fixed record order, exact byte counts per stream, no
   WATCHDOG_FIRED/ABORT. The input is bounded to 64 KiB, 2000 lines, 512-byte lines, ASCII and LF.

The sweeps confirm that no single line deletion, duplication, adjacent swap or
truncation of a valid log passes, including when seq and byte counts are rebuilt.
A seeded 3000-case byte-corruption run never crashes the assessor.

## What the current reader cannot establish (source-based)

1. **Provider exit before release.** The reader only checks that SIGUSR1 came from
   its parent (line 148). Its usage text says so: "no provider-exit proof inside reader".
2. **Timing between processes.** HELD and RELEASED carry no timestamps. Ordering
   between streams rests only on the controller's records (assumption A7). The provider
   trace catches a premature probe only if the provider was still dispatching. A release
   sent after the provider's loop broke but before it was reaped would not appear in any log.
   Preventing it is a matter of the controller's source (signal strictly after `wait` returns), not of the log.
3. **Silent early failures.** The `getppid()` mismatch returns 2 (line 102) and the signal-setup
   failures return 1 (lines 105–117), both before any output. The assessor sees an empty reader
   stream and a status, and can only say the run is incomplete.
4. **Unexplained stops.** Fixture, link, open or fstat failures (lines 118–131) go to
   `done` with no record and print only the generic STOP. The assessor can say "stopped before HELD", not why.
5. **Missing final markers.** If the 25 s budget is exhausted, `arm()` fails and STOP is not
   printed (line 184). A close over its bound returns 1 after its OP_END and prints no STOP
   (line 178). The assessor never passes these, but its diagnosis rests on the exit status.
6. **Whole-trial duration.** Only per-operation elapsed values are logged. The reader's
   budget rounds up to whole seconds (about 1 s over is possible), and the shell has no ms clock.
   Total trial time cannot be checked from this log; the controller watchdog must cover it.
7. **Kill encoding.** A SIGALRM kill shows up only as an exit status. The 128+n reading
   (142 for QNX SIGALRM=14) is assumption A5 and is used only to label the result.
8. **Implicit checks.** The readlink target and fstat size are not printed. Reaching
   CONTROL_BEGIN implies they passed.
9. **Output blocking.** The reader writes protocol records to stdout only. If the controller
   gives it a pipe that it doesn't drain, a write could block until the alarm. Redirect each
   child stream to its own file, as §3 of the contract assumes.

## Open choices for the contract review

- Should the controller itself validate the control trace before releasing, with an extra
  record such as `TRACE_CONTROL_OK`? The provider prints its trace before exiting, so this is possible.
  Without it, a bad control still cannot pass, because the assessor rejects it afterwards.
  It just means the probes ran under an invalid control. Keeping the assessor authoritative keeps the shell simpler.
- A6 (byte counting on the target) and A5 (shell status encoding) need checking against
  the car's actual shell and utilities before the controller is written.
- A3 (control seek reply code exactly -1) is deliberately strict. Relax it only after review.
- Binary identity relies on the pinned RAM names (A8); hashes stay with the read-back step.

## Not established by any PASS

That the capture is authentic or complete beyond its own framing; that the RAM
binaries matched their hashes; any general QNX error semantics (errno is recorded,
not interpreted); forced provider death, an in-flight request at death, larger bodies,
XML, plugin loading, HMI lifetime or live RPM.
