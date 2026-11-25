> Owner-supplied independent review from Claude, retained below as submitted.
> Read the [integration assessment](2026-11-25-larger-body-endpoint-assessment.md)
> for verified findings, corrections and target-specific limits. This report
> is static/offline analysis, not a vehicle procedure or a new test result.

# Independent review: moving the inert endpoint beyond 23 bytes — 25 November 2026

Scope: static/offline only. Read: `endpoint_policy.c/.h`, `nbt_endpoint_rehearsal.c`,
`test_policy.py`, `test_support/fake_qnx.h`, `README.md`, `READER-TRACE.md`,
the endpoint/stdio vehicle result notes, `STATUS.md`. I re-disassembled the
native loader at 0x298a570 in the original HmiMain3D (patched copy, `_stack`
index fixed). I did NOT re-read `nbt_stdio_reader.c`, `test_loop.py` or the
`.sh` runners this turn; statements about them come from your docs.
No plugin activation, firmware change or live-RPM inference is involved.

## 1. Verdict

The serving logic is already length-generic. The 23-byte assumptions sit in
three other places: the host tests, the C reader, and the lack of observation
of what libc actually sends. No change to `nbt_endpoint_slice` is needed.
A larger-body rehearsal needs a new build (a body generator, request logging)
and new host tests, not a rewrite.

## 2. Where 23 bytes is baked in

| Location | Assumption | Effect at 586 / 2048+ |
| --- | --- | --- |
| `endpoint_policy.c:4` | body is a string literal; length is `sizeof-1` | fine, but see NUL note below |
| `nbt_endpoint_rehearsal.c:144` | `attr.nbytes = nbt_endpoint_length()` | correct and single-sourced; keep it. A mismatch would break SEEK_END/ftell |
| `test_policy.py::test_full_read` | literal `b'nbt-endpoint-rehearsal\n'` | must become expected-hash/pattern |
| `test_policy.py::test_past_eof` | `slice(100,100) == (0,len,0)` | **would fail** at 586 (100 < len) — hard-coded "100 is past EOF" |
| `test_policy.py::test_random_read_boundaries` | offsets `-4..70` | covers EOF boundary only because len=23; for 586 it never reaches EOF |
| `test_partial_reads_reassemble` | chunks `(1,2,3,7,23,4096)` | the `23` chunk is len-specific; add len-1, len, len+1 |
| `test_policy.py` setup | `lib.nbt_endpoint_text` is `c_char_p` | truncates at first NUL; use `c_void_p` + `ctypes.string_at(ptr, length)` |
| stdio reader (per READER-TRACE) | rejects length != 23, fixed stack buffer, known-bytes check | must be parameterised (or a sibling reader) with length/hash inputs; heap or larger bounded buffer for 8192 |
| `check_deadline.sh` / `check_stdio_alias.sh` | expect the 23-byte text/size | need size+hash comparison |
| 5 s reader alarm / 10 s lease | sized for one tiny read | fine for ~10 requests; keep, but log elapsed time |

NUL note: a plain XML-like body has none, but the host tests should not rely on
C-string semantics anyway.

## 3. Body choice for the rehearsal

Use inert generated filler, not XML and not any piece of the real manifest.
Make each byte position-dependent (e.g. 16-byte lines containing an 8-digit
hex offset) so that duplicated, dropped or reordered chunks are detectable —
a 23-byte string cannot reveal that. Compare SHA-256 (or a simple
fold checksum if the target has no sha tool) rather than eyeballing.
Suggested sizes: 586, 2047, 2048, 2049, 4095, 4096, 4097, 8192, 8193.
The 2048 neighbours are included to test, not to assume, a boundary at
`msg_max_size`; the 4096 neighbours because common stdio buffers are
that size (the QNX libc buffer size is unobserved — see §5).

## 4. msg_max_size vs reply limits

What the QNX documentation I could reach says (6.6 resmgr guide and the
Getting Started "data structure sizing" page; the 6.5 library-reference pages
were not on my fetch allowlist, so these are neighbouring-version sources):

- `msg_max_size`: "controls how much buffer space the resource manager library
  should set aside as a receive buffer"; at least the biggest message header;
  data beyond the header is "not guaranteed to be present in the buffer".
- `nparts_max`: size of the outgoing `iov` array; "no effect on the incoming
  messages — only used on outgoing messages".

Applied to this code:

- A read *request* (`io_read_t`) is a small fixed header regardless of
  `nbytes`, so a read of 8192 does not need a larger `msg_max_size`.
  2048 is therefore not a read limit. Don't raise it "to be safe"; that would
  change an unrelated variable.
- `_RESMGR_PTR` builds a one-part iov pointing at static memory
  (`nparts_max = 2` is sufficient; it only needs >= 1). The reply is not
  copied through the receive buffer, so the incoming size does not bound it.
- What bounds a reply here: `count` (clamped to remaining by the slice) and the
  client's own receive size (`msg->i.nbytes`, signed 32-bit per your SDK
  capture). `ctp->status` (set by `_IO_SET_READ_NBYTES`) and the iov length are
  both `count`; keep them derived from the same variable.
- Where `msg_max_size` *does* matter: connect messages (open path + header) and
  write payloads. Writes are refused with EROFS before any data is touched,
  which is the right shape given the "beyond header not guaranteed" note.
- **Unknown, not assumed:** whether the 6.5 resmgr/kernel path imposes any
  other cap on a single-iov reply of several KB. The tests below determine it.
  Success at 8192 would show only that 8192 works on this unit, not a general
  limit.

## 5. What libc will actually send (unobserved)

Native evidence so far: one `fread(buf, 23, 1)` succeeded. Nobody has seen the
read requests the endpoint received. For a 586/4096/8192-byte item, libc may issue
one read of the item size, several buffer-sized reads, or a probe read after the
last byte. All of those are valid; the server handles any of them, but the
shape determines what else you must test. **Cheapest high-value change: record
each read `(ocb->offset, msg->i.nbytes, xtype, count)` and each lseek
`(whence, offset, result)` into a fixed in-memory array (e.g. 64 entries) and
print it once at the DETACHED line.** Do not print inside the handler. To log
lseek the endpoint must wrap `io->lseek` and call the SDK default; that is the
only functional addition suggested. Print-at-exit keeps timing unaffected and
leaves the lease logic unchanged.

## 6. Seek semantics

Native proof: SEEK_END → ftell==23 → SEEK_SET → full read, with the SDK default
lseek and `attr.nbytes`. Not proven: SEEK_CUR, SEEK_END with a negative offset,
seeking beyond EOF, negative resulting offsets, and what the SDK default
returns for each (I couldn't fetch its 6.5 page; don't rely on my memory of it).
The server side is safe regardless — `nbt_endpoint_slice` returns EINVAL for
negative values and a zero-length read for offsets at/after EOF, with no wrap
at 2^63-1 (tests exist). Native test matrix with a body of 586 bytes first:

1. SEEK_SET 0 / 100 / len-1 / len / len+1000, then read 1, 10, len.
2. SEEK_CUR after a partial read: +0, +10, -5, and one that would go negative.
3. SEEK_END with 0, -10, -len, -(len+1), +10.
4. Expected EOF: read at len returns 0 bytes, repeatedly.
5. For each, record return value and errno; judge against the server log in §5.

Mark every result "observed on this unit" and none as general QNX behaviour.

## 7. Native-loader properties that matter (disassembly, 0x298a570)

- `fopen(path,"rb")` → null → early failure path (0x298a7e4).
- `fseek(f,0,SEEK_END)` and `fseek(f,0,SEEK_SET)` return values ignored.
- `ftell` result (r6): `cmp r6,#0; bne` — **zero** closes the stream and
  fails; **-1 is not treated as an error**. It continues to `malloc(len+1)`
  = `malloc(0)`, then `fread(buf, 0xFFFFFFFF, 1, f)`. An endpoint whose
  SEEK_END failed could therefore make HMI write file bytes into a ~0-byte
  buffer. This does not happen on the tested path (ftell==23), but it is the
  concrete reason `attr.nbytes` and lseek behaviour must be verified for
  *each* body size before any real manifest is served, and why the lease
  design must never serve a manifest from a server whose lseek is
  unverified at that size.
- Short or failed `fread` (`cmp r0,#1; beq`): the failure branch (0x298a644)
  calls an error routine and then `fclose(r4)` at 0x298a664. The success branch
  closes at 0x298a674. So within this function the stream is closed on both
  paths, which is good for the "open handle at provider death" concern in HMI;
  the window is only the duration of these few calls. Not verified: the other
  callers, and fd/handle behaviour inside the error routine.
- `fread` with item size = length and count 1: a short read from the server
  yields 0 items and fails the load, even if the bytes so far are correct.
  Whether QNX libc loops over multiple short `read()` replies to fill one
  large item is unobserved. The §5 log plus reads at 4096/8192 answers it.

## 8. Provider death with an open client handle (untested)

All native results so far have the client finish (`fclose`) before the server
expires or dies; the SIGKILL case had no open client. So the following is
untested: client fd open, server expires/is killed, then client does `read`,
`lseek`, `fstat`, `close`.

- Server-side shutdown uses `resmgr_detach(..., _RESMGR_DETACH_ALL)` while
  the handle is open. What detach does to open OCBs, and what the client sees,
  I could not confirm from available documentation. Don't assume.
- Proposed test (inert reader variant, own fixture, own PIDs): reader opens the
  alias, reads half the body, sleeps past the lease, then tries
  read / lseek(SEEK_CUR,0) / fstat / close, recording `errno` each time under a
  hard alarm. Run twice: normal deadline and helper SIGKILL. Expected
  outcomes are unknown; the point is to see that nothing blocks forever and that
  the process exits.
- Pass criteria: every call returns (success or error) before the alarm; no
  hang in `close`; the server is gone; the fixture is cleaned.
- Do not extrapolate to HMI: its loader holds the handle for a few calls, and
  guard-death timing in HMI is a separate unreviewed problem.

## 9. Proposed offline checks before any new vehicle command

1. Parameterise the body in the policy module (build-time length + pattern),
   keeping `nbt_endpoint_length()` as the only source for both `attr.nbytes` and
   slicing. Add a compile-time guard that the length fits in `int` and is below
   a chosen cap (e.g. 16384) so a future edit cannot silently serve a huge body.
2. Rewrite the host tests to be length-agnostic: derive "past EOF" from
   `len`, exercise offsets `len-1, len, len+1`, powers of two ±1, and chunk
   sizes `1, len-1, len, len+1, 2047, 2048, 2049, 4096, 8192`; compare against
   the pattern generator, not a literal. Add `string_at` for the body.
3. Extend the `fake_qnx` loop test (`test_loop.py`) with a read of a larger
   body to confirm the actual `endpoint_read` produces iov length == status
   == count and advances `ocb->offset` by `count` exactly (the fake's
   `_RESMGR_PTR` already records both). This remains a host check, not QNX.
4. Static-check the new reader: bounded buffer sized from a validated length,
   checks every `fseek/ftell/fread/fclose` result, rejects `ftell < 0` (which the
   native loader does not), alarm retained.
5. Cross-build with the same SDK image; repeat the ELF/import review. Diff
   the imports against `83c6e473829e` and the reader's (`lseek` wrapper
   will add nothing new beyond the default symbol).
6. Native order (when you choose to resume): help-only → 586-byte read via
   `cat` → stdio reader at 586 → 2047/2048/2049 → 4096/8192 → seek matrix →
   death-with-open-handle. Stop at the first anomaly.

## 10. Unknowns that remain after all of the above

- Whether the real HMI scanner/XML parser will accept the symlink-backed alias
  (scanner `stat` is traced; admission beyond it is not).
- Real-manifest behaviour: TinyXML-style parse, `{pluginDir}` expansion, library
  path handling and fallback — none exercised.
- HMI guard identity and lifetime; whether discovery removal affects loaded code
  (per STATUS.md: it does not unload).
- The earlier mixed-runtime stream-destructor crash and the unit restarts remain
  unresolved and are independent of file size.
- Nothing here bears on whether `engine.RPMSpeed` will carry live data.

## Sources

- QNX docs, resource manager attributes: https://www.qnx.com/developers/docs/6.6.0.update/com.qnx.doc.neutrino.resmgr/topic/skeleton_InitResMgrAttr.html
- QNX docs, data structure sizing: https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_resmgr_dsize.html
- Repo files named above; HmiMain3D original SHA-256 027cf939…b8cf (disassembly of a metadata-patched copy).
