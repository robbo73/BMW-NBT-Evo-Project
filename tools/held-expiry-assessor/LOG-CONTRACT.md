# held-expiry-log/1 — PROPOSED log contract

**Status: PROPOSED — Codex proposal revision 2.** See [REVIEW.md](REVIEW.md)
for the original-upload fingerprints, reproduced gaps and amendments. This
version adds CONTROL_TRACE_OK and moves WATCHDOG_CANCELLED after cleanup.
No prior controller implemented revision 1; this remains held-expiry-log/1.

 No controller implements this yet. The `HXC1` controller
records below are new and need review before anyone writes the controller.
The reader (`nbt_hold_reader.c`, held-reader-1) and the provider
(`nbt_large_endpoint_586`, 8f502b63…) are **not changed**. Their output is
carried verbatim inside stream sections.

Basis: commit cb4c8c0. Reader format strings in `nbt_hold_reader.c`
lines 133–184; provider trace formats in `tools/larger-body-rehearsal/trace_log.c`
and `nbt_large_endpoint.c` lines 174–211.

## 1. File-level rules

- One capture is one trial. The file is exactly what the controller emitted.
  It must not contain transport preamble, checksum output or hand-edited text.
- Bytes: printable ASCII (0x20–0x7E) and LF only. No CR, TAB, NUL or UTF-8.
- Every line ends with LF, including the last line (a missing final LF counts as truncation).
- Limits enforced by the assessor: 65536 bytes, 2000 lines, 512 bytes per line.
- The first line is `HXC1 seq=1 BEGIN …`; the last line is an `END` record.
- Every line outside a stream section is an `HXC1` record. Any other line is malformed.

## 2. Controller record grammar (PROPOSED)

```
HXC1 seq=<n> <EVENT> <key=value ...>
```

- `seq` starts at 1 and increments by exactly 1 across all `HXC1` records,
  including `SECTION_BEGIN`/`SECTION_END`. It exposes dropped or reordered records.
- Keys appear in the fixed order shown; extra or missing keys are malformed.
- Integers are canonical decimal (no leading zeros, no `+`, no `-0`).
  PIDs are 2..2147483647. Statuses are 0..255.
- `C` is the controller process PID; `P` is the provider PID; `R` is the reader PID.
  The controller must be the reader's direct parent. It need not be a shell.

### Required sequence for a complete trial

| # | Record | Meaning (controller's claim) |
| --- | --- | --- |
| 1 | `BEGIN contract=held-expiry-log/1 controller=held-controller-1 controller_pid=C provider_bin=/dev/shmem/nbt_large_endpoint_586_8f502b6394a0 reader_bin=/dev/shmem/nbt_hold_reader_586_9a54c7f4dba5 fixture=/ramdisk/mm/.nbt-held-alias-586.C` | Pinned RAM names; actual hash read-back verification is separate |
| 2 | `PROVIDER_STARTED pid=P` | Exact owned child started |
| 3 | `PROVIDER_READY pid=P path=/dev/nbt_large_endpoint_586.P` | Complete matching READY observed |
| 4 | `ALIAS_CREATED path=<fixture>/dummy-body.bin target=/dev/nbt_large_endpoint_586.P` | Owned symlink created |
| 5 | `READER_STARTED pid=R parent=C provider=P` | Reader is C's direct child |
| 6 | `HELD_OBSERVED reader=R` | Complete matching HELD observed |
| 7 | `PROVIDER_REAPED pid=P status=S` | Exact child reaped, normal status 0 required |
| 8 | `ENDPOINT_ABSENT path=/dev/nbt_large_endpoint_586.P alias=dangling` | Endpoint absent and alias still a dangling link |
| 9 | `CONTROL_TRACE_OK provider=P events=2` | Controller validated the actual complete provider trace and stderr against section 4 before release |
| 10 | `RELEASE_SENT reader=R signal=USR1` | Signal only after all four prerequisites: 6, 7, 8, 9 |
| 11 | `READER_REAPED pid=R status=S` | Exact reader reaped, normal status 0 required |
| 12–19 | Four `SECTION_BEGIN`/`SECTION_END` pairs: provider.stdout, provider.stderr, reader.stdout, reader.stderr | Separate bounded complete captures |
| 20 | `FIXTURE_CLEANED path=<fixture>` | Only owned fixture removed and checked |
| 21 | `WATCHDOG_CANCELLED` | Coverage retained through cleanup/output sections; no firing |
| 22 | `END result=complete` | Complete controller path |

CONTROL_TRACE_OK is a controller assertion that must be backed by its actual
source checks, not merely printed to satisfy this parser. The final assessor
still independently validates the framed provider trace. No record authenticates
which code ran or establishes causal action ordering by itself.

### Failure records (any of them makes PASS impossible)

```
HXC1 seq=<n> WATCHDOG_FIRED target=provider|reader|both
HXC1 seq=<n> ABORT reason=<token [a-z0-9_]{1,40}>
HXC1 seq=<n> END result=aborted
```

On an abort path the controller should still emit any stream sections it has,
so the run can be diagnosed. The assessor parses sections wherever they appear.

## 3. Stream sections

```
HXC1 seq=<n> SECTION_BEGIN stream=<name> bytes=<B>
<verbatim child output lines>
HXC1 seq=<n+1> SECTION_END stream=<name>
```

- `B` is the exact byte count of the payload lines, including their LFs. It catches truncation.
- Payload lines must not start with `HXC1 `; neither child emits that prefix.
- Each stream appears exactly once. Both `*.stderr` sections must be empty
  (`bytes=0`) for PASS: the provider uses `perror` only on failure, and the reader
  writes nothing to stderr, so any loader or libc message there is a failure.
- Separate capture removes interleaving between the three processes.
  Ordering *between* streams comes only from the controller's records.

## 4. What the assessor requires inside the sections

Provider stdout, exactly these lines in this order:

```
READY pid=P path=/dev/nbt_large_endpoint_586.P bytes=586 lease_ms=10000
TRACE_SUMMARY events=2 dropped=0 overflow=0 elapsed_ms=<>=10000>
TRACE_READ index=0 before=0 requested=100 xtype=0 count=100 after=100 rc=-1
TRACE_SEEK index=1 before=100 offset_bits=0000000000000000 whence=1 after=100 rc=-1
DETACHED reason=deadline; endpoint server exiting
```

Reader stdout: the held-reader-1 lines, unchanged:
`CONTROL_BEGIN/END read100` (rc=100), `CONTROL_BEGIN/END seek_current` (rc=100),
`HELD pid=R parent=C provider=P offset=100`, `RELEASED sender=C`,
`OP_BEGIN/END` for `read64_a`, `seek_start`, `read64_b` (each rc=-1, errno ≥ 1,
0 ≤ elapsed_ms < 3000), `OP_BEGIN/END close` (rc 0 with errno 0, or rc -1
with errno ≥ 1; elapsed < 3000), then the `OBSERVED:` line.

**Two meanings of `rc`:**
- `TRACE_* rc=-1` is the provider's resource-manager reply code (`_RESMGR_NPARTS(1)`), not an error.
- The reader's `rc=-1` is the raw syscall return value. Only the reader's `rc=-1` means failure.

The assessor keeps these as separate fields (`endpoint_reply_code` and `syscall_result`).

## 5. Assumptions (each needs confirming before the controller is written)

- A1. SEEK_CUR is `whence=1` at the provider. Observed natively: the 586-byte transcript
  (`docs/evidence/2026-11-26-large-body-586-owner-transcript.txt`) shows whence 2, 1, 0 for
  SEEK_END, the `ftell` query (SEEK_CUR) and SEEK_SET.
- A2. The 100-byte control read produces exactly one provider read request with `requested=100`.
  This is the point of the control, so a different request fails it rather than being explained away.
- A3. The control seek reply code is `-1`, as every seek was in the native 586-byte trace. Any other code is
  refused rather than interpreted; relax only after review.
- A4. The provider's `elapsed_ms ≥ 10000` for `reason=deadline`. Source basis: the loop breaks when
  `now >= started + 10000`, and elapsed is measured from the same `started`. There is no upper bound; the value is reported.
- A5. Status is normalized to 0..255, with 128+n for a signal. Native helper
  SIGKILL status 137 was previously observed; SIGALRM=14 is in the SDK, but its
  status 142 is a diagnostic convention, not a new vehicle observation. A C
  controller must decode raw waitpid status instead of logging raw status bits.
- A6. The controller must count bytes in each bounded capture. A C controller
  can maintain counts directly; no shell byte-counting utility is assumed.
  Overflow or incomplete capture must abort; do not omit bytes=.
- A7. Records are emitted by the controller in the order it performed the actions. The log cannot prove this (see the integration note).
- A8. Binary identity rests on the pinned RAM names; hashes are verified by read-back outside this log.

## 6. Remaining controller requirements

This log does not contain a whole-trial timestamp. A PASS is not evidence of
the 25-second whole-trial limit; watchdog implementation, coverage through
capture/cleanup/output, cancellation and bounded child reaping need source
review and tests. A watchdog that only signals children does not by itself
bound a stuck controller. Decide how blocked controller IO is bounded before
implementing the target runner. Keep child captures bounded and preserve them
without editing before framing. No firmware/reader/endpoint change follows.
