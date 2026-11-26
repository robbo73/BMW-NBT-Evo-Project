> Owner-supplied Claude proposal, received 26 November 2026. External static
> analysis, not a native result or an instruction to execute. The original
> document follows verbatim after this header. See the companion
> [integration assessment](2026-11-26-open-handle-expiry-assessment.md) for
> corrections and remaining design requirements.
>
> Original upload: 10846 bytes; SHA-256 `963c12d3dd3feb689f7ab710b1706e7250424ac54cd766f79797f4b4e964c631`.

---

# Smallest next test: provider expiry while a reader holds the file open — proposal only

26 November 2026. Static review of commit 4ef1c50 (`tools/larger-body-rehearsal/*`,
`docs/2026-11-26-larger-body-vehicle-results.md`). Nothing implemented, built or run.
Kept separate from larger sizes and from HMI integration. "Source" below means
the repo's own C/shell as read; "QNX runtime" means something only the car can answer.

## 0. Acknowledging the 586-byte result

Your four-event trace matches the source: `endpoint_lseek` wraps
`iofunc_lseek_default` and records before/after, `endpoint_read` records the request
(`nbt_trace_read`, line 47), and `-1` is `_RESMGR_NPARTS(1)`-style reply coding, not a
failed seek (your reading is right). The result I care about most for this test:
**libc asked the provider for 1024 bytes to satisfy a 586-byte `fread`.** So stdio
did read-ahead into its own buffer, which is exactly the trap in your question 1.

## 1. What the current code cannot do (source)

- `check_large_alias.sh` runs the reader in the foreground (line 93) and only then
  `wait`s for the server (line 96). The reader therefore always finishes before
  expiry; the open-handle case is structurally impossible without restructuring
  the runner (reader backgrounded, released after the server is reaped).
- `nbt_large_reader.c` arms `alarm(5)` at line 57 and clears it at line 96 with
  `SIGALRM` at `SIG_DFL`. A reader that sleeps past the 10 s lease would be killed
  at about t+6 s, before expiry. Your instinct is correct: it cannot stay as is.
- The 15 s watchdog (script lines 82–88) kills only `$nbt_server`.
- The trace wraps only read and lseek. Open, stat and close are untraced.
- After the loop breaks (endpoint lines 177–198) the server never dispatches again:
  detach, free, destroy, dump, exit. So after the deadline nobody is serving
  messages, even briefly.

**Consequence:** the endpoint binary (8f502b63…) can be reused unchanged. The smallest
test is a new sibling reader plus a new runner. Leave the frozen reader, endpoint
and package untouched.

## 2. Question 1 — make sure post-expiry operations reach the provider

1. **Use raw descriptors for the held phase:** `open`, `read`, `lseek`, `close`
   (optionally `fstat`). No `FILE*`. Stdio is where the 1024-byte read-ahead lives;
   `fread`/`fgetc`/possibly `ftell` can be answered from that buffer after the
   provider is gone. Whether this libc's `read()` has any client-side cache is a
   QNX runtime question, so do not assume it; control it (next point).
2. **Pre-expiry control in the same run.** Before holding: `read(fd, buf, 100)`
   and compare with the body oracle's bytes 0–99, then `lseek(fd, 0, SEEK_CUR)` and
   require 100. The unchanged server's trace must then show exactly
   `READ before=0 requested=100 count=100 after=100` and `SEEK before=100 whence=SEEK_CUR`.
   `requested=100` (not 1024) proves no read-ahead for raw `read()`. If the trace
   disagrees, the run is INVALID for interpreting the post-expiry probes.
3. **Choose probes whose success cannot come from the client:**
   - `read(fd, buf, 64)` at offset 100. Offset is far from EOF (586), so a
     0-byte return cannot be our own EOF logic. Any success is anomalous.
   - `lseek(fd, 0, SEEK_SET)` — pre-expiry this reaches the provider (it is
     in the trace today), so it is a valid provider probe.
   - a second `read(fd, buf, 64)`, to see whether the first outcome is stable.
   - `close(fd)` — record only. A close can succeed on the client side
     without a live provider, so it is not evidence either way.
   Do **not** use `fcntl(F_GETFL)` or similar as a probe: on QNX some descriptor
   state is plausibly answered without a provider message (unverified), so its
   success would be exactly the misleading kind.
4. **Establish "provider gone" independently of the held fd.** The runner (not the
   reader) reaps the server with `wait` and requires exit 0, then checks the
   endpoint path no longer resolves; only then does it release the reader.
   Do not release on a timer, and do not have the reader poll `stat()` on the
   endpoint (that sends connect messages to a provider that may be mid-exit).

## 3. Question 2 — bounding the client across the ten-second lease

Timeline from source: server starts t0; runner `sleep 1` (line 89); reader starts
≈ t0+1 s; server deadline = t0+10 s; runner reaps ≈ t0+10.02 s; watchdog would
kill the server at t0+15 s if it overruns.

| Phase | Mechanism | Bound |
| --- | --- | --- |
| A: open, validate, control read/seek | existing `alarm(5)`, re-armed at start | 5 s, ends well before expiry |
| B: hold | re-arm `alarm(18)` on reaching HELD; block `SIGUSR1`, install handler, `sigsuspend` loop until flag set | 18 s from ≈ t0+1.2 s = t0+19 s, beyond even the t0+15 s watchdog path |
| C: probes | re-arm `alarm(3)` before every operation; markers before and after each | 3 s per op |

- The runner releases the reader with `kill -USR1` only after the server exit
  is reaped, the path is absent, and `kill -0` shows the reader still alive.
  The reader blocks `SIGUSR1` before it announces HELD, so a signal cannot be lost.
  The runner does `wait` on the reader (backgrounded child), then collects its
  status.
- Extend the existing watchdog pattern (kills only its own children) so a stuck
  reader is also `SIGKILL`ed at a later fixed time, e.g. t0+25 s.
- Keep `SIGALRM` at `SIG_DFL` as in the reviewed reader; a handler cannot help if
  the thread is blocked in a send.
- **Marker output must survive being killed:** write markers to stderr or `write(2)`
  (unbuffered), not buffered stdout. The existing reader's `printf` of PASS is
  lost if `SIGALRM` fires first.

## 4. Question 3 — telling loss, hang and misleading success apart

The reader prints one record per phase boundary: `HELD t=…ms`, `RELEASED t=…ms`,
`OP_BEGIN name`, `OP_END name rc=… errno=… elapsed_ms=… bytes=… match=…`.
Errno is recorded, not asserted; no value is hard-coded as "correct".

| Verdict | Observations required |
| --- | --- |
| **EXPECTED LOSS** | Control passed (trace shows the two expected events, `requested=100`). Server `DETACHED reason=deadline`, exit 0, reaped before release. Path absent. Every probe returns -1 (close excepted) quickly (< per-op bound), every `OP_END` printed, reader exits by its own logic. Server `elapsed_ms` ≈ 10020 as before. |
| **MISLEADING SUCCESS** | Any probe returns success after the release: bytes matching the oracle, a 0-byte read at offset 100, or `lseek` returning an offset. The provider was reaped, so this needs explaining before any further step. It also means held-fd results cannot be read as "endpoint loss". |
| **HANG** | Reader terminated by `SIGALRM` after an `OP_BEGIN` without `OP_END`; or any probe elapsed ≥ bound; or runner watchdog line; or no `DETACHED` line. The last marker names the stuck operation. |
| **INVALID / NO-GO** | Reader never reached HELD; `SIGUSR1` not received before the Phase B alarm (no `RELEASED` line); server did not exit 0 with `reason=deadline`; trace control mismatch. Nothing is concluded about expiry. |

Also compare the server's `elapsed_ms` with the 10020 ms baseline: a notably
larger value would suggest the held binding delayed detach.

Do not generalize: a pass says only what a raw-fd client observes on this unit
for this dummy provider after a normal deadline exit.

## 5. What the QNX 6.5.0SP1 documentation supports

From the `resmgr_detach` page for 6.5.0SP1 (https://www.qnx.com/developers/docs/6.5.0SP1/neutrino/lib_ref/r/resmgr_detach.html):

- `_RESMGR_DETACH_ALL` "detach[es] the name from the namespace and invalidate[s]
  all open bindings"; `_RESMGR_DETACH_PATHNAME` leaves existing bindings intact.
- For an existing connection "the I/O callout table is redirected" and "the client
  will receive an error of EBADF when it uses the fd".
- `resmgr_detach` "blocks until the `RESMGR_HANDLE_T` … isn't being used in any
  connection function" — i.e. connection functions, not a client idle with an open
  fd.

Implication: the documented EBADF is a statement about a provider that is **still
dispatching** after detach. Our server exits instead, so what the client sees
may be a different, dead-channel error that the documentation here does not name.
Either result is informative. Do not pre-write one as the pass criterion.

## 6. QNX runtime questions this test would answer (and does not presuppose)

1. The error (and latency) a raw-fd `read`/`lseek` returns when the provider process
   has exited with an open binding. EBADF is documented only for the still-dispatching case.
2. Whether `close()` on that fd succeeds, fails or blocks.
3. Whether `detach(ALL)` with an idle open binding changes the 10020 ms exit time.
4. Whether a `SIGUSR1`-driven release works as expected in this shell/libc (the
   passed delivery tests used `SIGHUP`).
5. Whether libc `read()` caches anything (answered only by the control trace).
6. Not answered (needs a separate case): a read already blocked while the
   provider dies, and whether `SIGALRM` interrupts a client blocked in a send to a
   live-but-not-dispatching server. The layered watchdog exists for that
   reason; the earlier forced-death tests had no client attached.

## 7. Offline checks before anything goes to the car (follow your existing pattern)

- Pure classifier function tested exhaustively on injected results (loss, success,
  0-byte read, partial, timeout, missing markers, control mismatch).
- Host fault binaries for: held reader released normally; `SIGUSR1` sent before
  `sigsuspend` (race); `SIGUSR1` never sent → NO-GO and bounded exit; a probe
  stalled by your `pause`-based wrapper killed by the per-op alarm with the last
  marker `OP_BEGIN`; marker output intact after `SIGALRM` death.
- Runner tests with stubs: server exit non-zero or wrong reason → no release;
  endpoint still resolving → no release; reader still alive check;
  watchdog kills only its own two children.
- New ELF/import review for the sibling reader (`sigsuspend`, `sigprocmask`,
  `sigaction`, `clock_gettime`, raw `open/read/lseek/close`) against the car libc
  exports, as you did for the stdio reader, plus a hash-pinned RAM copy.
- Run order when you choose to resume: help-only, then one normal-deadline run.
  Only if that is clean consider a second run with the helper `SIGKILL`ed; a
  detach-then-keep-dispatching server variant (to see the documented EBADF) is a
  separate, later change.

## 8. Not covered

No HMI claim follows. The native loader holds the stream for a few calls and
closes on every path I disassembled (0x298a570), so this scenario is mostly about
unexpected stalls and guard death, not the normal load. No plugin, XML, RPM,
larger sizes or restart investigation is involved.
