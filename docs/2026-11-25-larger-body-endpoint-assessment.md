# Larger-body review: integration assessment — 25 November 2026

The owner asked for the useful parts of Claude's attached review to be
added to GitHub. The [submitted report](2026-11-25-larger-body-endpoint-review.md)
is retained as supplied after an attribution header. Original upload:
12371 bytes, SHA-256
9d9866cd2f4c07a37c73f9b304037587ab2820e5c8b2499e6502f63144886a6b.
Instructions/proposed tests in that report are review material, not commands
that were run or authorization to load a real plugin.

## Findings accepted from source inspection

| Finding | Assessment |
| --- | --- |
| Slice bounds and stat size derive from nbt_endpoint_length() | Confirmed. The slice algorithm has no 23-byte constant; controlled larger bodies can retain that design with an explicit size cap. No generalized body exists yet. |
| Host tests contain small-body assumptions | Confirmed: literal expected text, offset 100 assumed beyond EOF and random offsets limited to -4..69. Future cases must derive boundaries from the selected length. |
| ctypes c_char_p treats data as a C string | Confirmed. A binary-safe test should read the pointer plus explicit length, including embedded-NUL cases. |
| Existing C reader rejects sizes other than 23 | Confirmed. It also already rejects ftell==-1 through its exact-length check; this is not a newly discovered defect in our reader. A larger sibling needs validated bounded lengths and storage. |
| Read/seek request tracing would be useful | Accepted as a proposed bounded instrumentation change, not an implemented feature. Actual libc request sizes remain unobserved. |
| No provider-death test with an open client handle | Confirmed for the supplied native transcripts: reads closed before the tested helper stop/death. Future behavior remains unknown. |

The existing fake header records read status and an IOV pointer/length, but
the current fake dispatcher does not call the actual read callback. A future
larger-body check must exercise that callback and assert status, IOV count/
length and OCB offset together. The stub has no lseek model; extending it
would test control flow only, not SDK ABI or actual QNX seek semantics.

## Native loader: unchecked negative length, with corrected allocation wording

Fifteen original ARM instructions plus the allocation veneer/import were
checked against the unchanged captured HmiMain3D (SHA-256
027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf).
See the [static audit](2026-11-25-loader-length-audit.json).

The loader compares the saved ftell result with zero at 0x298a5e0, and
branches for any nonzero value. It does not explicitly reject -1. If the
returned 32-bit length were -1, the add at 0x298a61c would wrap the requested
allocation size to zero, while the fread item size loaded at 0x298a624 would
remain 0xffffffff (count 1 at 0x298a628).

**The call at 0x298a620 is the C++ array allocation operator (`operator new[]`), not `malloc`.** Its
veneer at 0x2b28630 resolves to the _Znaj import at 0x2781ec. The submitted
report's malloc(0)/approximately-zero-buffer wording is therefore corrected
here. Allocator normalization, allocation failure/exception behavior and
libc's handling of that huge fread argument have not been established.
This is an unchecked-length path in static code, not proof of an observed
heap overwrite or the cause of the earlier unit restarts. Do not provoke
this case in HMI.

Normal control flow explicitly closes the stream at 0x298a5f0 for zero
length, at 0x298a664 after the failed full-item read, and at 0x298a674 after
a successful read. This does not prove cleanup during every exception,
termination or blocking failure. The code requires fread to return one
complete item. A short underlying server reply does not alone establish
that the outer fread must fail; libc may issue further reads to complete
it. That request behavior is the proposed logging experiment's purpose.

The current C-only reader checks both fseek results and requires length 23
before using its fixed buffer. Its tested native success remains valid.
Any larger reader must likewise reject negative, unexpected or excessive
lengths before buffer access. No source change was required for the existing
reader to reject a negative ftell result.

## Message sizing: distinguish SDK facts, other-version docs and target unknowns

The captured installed 6.5 SDK shows signed 32-bit read nbytes,
_IO_SET_READ_NBYTES setting the context status, and _RESMGR_PTR populating
one IOV pointing to the supplied memory and returning _RESMGR_NPARTS(1).
The actual code derives both status and IOV length from the same bounded
count. Those observations are independently supported by the capture.

The submitted report cites QNX **6.6** for resmgr attributes and **8.0** for
the Getting Started sizing page. Those are external, other-version sources,
not independently retrieved or verified 6.5 reference pages in this review.
They support a receive-buffer versus outgoing-parts interpretation; they do
not establish every limit of this unit's 6.5 stack. Do not assume that 2048
is a reply cap, increase it speculatively, or declare that every larger
reply is supported. Actual bounded native reads must establish the tested
sizes and request/reply behavior.

A direct lseek instrumentation wrapper may add a new required import:
iofunc_lseek_default is absent from the current helper's 33-import list.
The actual car libc exports it, but a new binary still needs its own import
review. Its callback must use the captured SDK signature and preserve the
SDK's return, status, IOV and OCB semantics; the sign of a callback return
alone is not an error classifier (_RESMGR_NPARTS is negative).

## Proposed next preparation, not implemented or executed

- Keep the existing 23-byte build/package frozen. Prepare a separate bounded
  body variant with position-dependent bytes, one authoritative length and
  an explicit cap fitting the SDK's status/length types. Cover 586 bytes,
  2047/2048/2049, 4095/4096/4097 and 8192/8193 in offline checks first.
- Use length-derived EOF/partial-read/offset boundaries, binary-safe expected
  bytes and exact reconstruction checks. Preserve write refusal and the
  existing receive-timeout handling; body growth does not justify unrelated
  protocol or lease changes.
- Record reads and seeks in fixed-capacity memory with a visible overflow/
  dropped-record indication. Avoid formatting/log IO in handlers and preserve
  callback semantics. Print-at-exit reduces handler IO but does not eliminate
  timing overhead, and SIGKILL cannot flush an exit log. Plan observation of
  forced-death cases separately and measure elapsed time.
- Review seek cases (SET/CUR/END, negative results and beyond EOF), actual
  requests, complete fread items and failure propagation before a new QNX
  cross-build/import review or any native run. Do not serve a real manifest
  through unverified seek behavior.
- Design open-handle-at-provider-death as a separate inert reader variant.
  Buffered stdio may satisfy a later read/seek from client-side cache, so
  cached success would not prove a live server operation. Use reviewed raw
  descriptor operations or explicitly controlled buffering and request
  evidence. Bound every blocking operation, including close. The current
  reader's five-second alarm cannot cover deliberately sleeping past a
  ten-second lease; choose coordinated, bounded test deadlines rather than
  merely reusing it. Expected OS errors/handle behavior remain unknown.

The proposed order remains incremental and stops on an anomaly, after the
new host checks, SDK/ELF review and fixed artifact pins. This document adds
no vehicle command, implementation, build output or completed larger-size
result. All suite counts and existing native 23-byte results are unchanged.

Real XML parsing/admission, resource lifetime, HMI identity/guard lifetime,
the earlier mixed-runtime crash and live RPM remain unverified. Endpoint
unavailability does not stop code already loaded into HMI. Actual plugin
loading and HMI activation/restart trials remain paused.


## Implementation follow-up

The owner returned to Ubuntu. A separate [bounded body/reader/trace
preparation](2026-11-25-larger-body-preparation.md) now passes 34 host checks
and a private captured-SDK callback declaration check. The first native
build will be 586 bytes only, for ELF review. No native result, real manifest
or change to the frozen 23-byte packages is implied.
