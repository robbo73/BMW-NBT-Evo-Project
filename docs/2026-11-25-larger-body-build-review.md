# Rebuilt 586-byte pair: ELF review and ready bundle — 25 November 2026

The corrected owner run passed all 36 tests in 11.604 seconds and built both
QNX executables. The uploaded archive is 39056 bytes, SHA-256
fc26f44da2c54ed22691b796b8a815b8144ef0d4c14b45e3e8768217190c5905.
Its exact 35-member set, ordinary-file extraction and all 18 preparation
payload hashes were checked; every source/metadata file matches the
host-fix preparation. No target source changed for this review.

## Compiled executables

| Field | Endpoint | Reader |
| --- | --- | --- |
| File | nbt_large_endpoint_586 | nbt_large_reader_586 |
| Size | 15898 bytes | 10248 bytes |
| SHA-256 | 8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2 | f0d391701c69a8dd07c203c876bbed1ef5d1a885604667b4ed64502f87745884 |
| Entry | 0x100b48 | 0x100834 |
| Required function imports | 34 | 22 |
| New required versus tested 23-byte tool | iofunc_lseek_default only | None |
| Relocations | 36 JUMP_SLOT; three COPY | 24 JUMP_SLOT; two COPY |

Both are ELF32 little-endian ARM ET_EXEC, flags 0x5000002, interpreter
/usr/lib/ldqnx.so.2, libc.so.3 only. All required function imports are
exported by the captured actual car libc. The endpoint's COPY objects are
_Stdout 80, errno 4 and _Stderr 80; the reader has errno 4 and _Stderr 80.
All sizes match provider exports. Only ordinary frame_dummy and
__do_global_dtors_aux init/fini array entries appear, with the two optional
weak frame-info hooks. There is no TEXTREL/RPATH/RUNPATH, unsupported
relocation, host fault/stub marker or C++ stream construction.
See the [audit metadata](../tools/larger-body-rehearsal/audit-build-2026-11-25.json).

## Actual callback/logging and reader checks

Thirty-four exact compiled instruction sites were checked across the pair,
in addition to inspecting the surrounding instructions:

- The endpoint body storage and constant length are exactly 586 bytes.
  Its generated pattern is initialized before attach. Read count/status,
  IOV base/length and OCB updates use the reviewed captured SDK offsets.
- Seek at 0x100dc0 snapshots unsigned request offset bits (+8), signed short
  whence (+4) and the OCB offset (+8) before calling iofunc_lseek_default at
  0x100dd8. It retains the result, records only value copies and returns the
  original result unchanged at 0x100e04. Callback-table assignment points to
  this wrapper. No SDK reply buffer is changed after the default call.
- Trace storage is 64 records of 56 bytes (3584 bytes). reserve compares used
  with 64, clears one 56-byte record for an accepted event, and otherwise
  increments a drop counter unless it is already ULONG_MAX. No formatting/IO
  occurs in these callbacks. Dump calls are in cleanup after detach/context
  free/destroy. Zero/missing elapsed time conditions remain explicit.
- The receive loop retains receive-ID classification, retry for EINTR/260
  timeout and failure for other errors. The inspected binary retains the
  ten-second deadline and 100 ms polling setting; incoming msg_max_size is
  2048 and nparts_max is two. No outgoing byte cap is inferred from them.
- The reader checks its fixed alias controls and seeks, explicitly rejects
  negative ftell at 0x100d5c, compares length with 586, requires one complete
  fread item, compares every byte and checks close. Its own five-second alarm
  remains. Default/help paths precede body/file operations in both programs.

These static findings do not establish native formatting, runtime alarm
behavior, request sizes, lseek results, larger replies or the new endpoint's
actual successful read. No ARM code was executed in the cloud.

## New runner and local trace assessment

The [runner](../tools/larger-body-rehearsal/check_large_alias.sh) reuses the
previously tested owned RAM fixture/child/expiry/cleanup pattern with the
new fixed executable names, alias namespace and reader. Nine Linux runner
cases pass (1.915 seconds), including the actual reader source built for
the host, failure propagation, missing/linked reader, missing endpoint,
overrun, unexpected-entry preservation and hangup cleanup. No actual QNX
namespace or IPC is emulated.

Its remote PASS covers only read/expiry/cleanup and says trace assessment
is still required. The [local checker](../tools/larger-body-rehearsal/assess_trace.py)
will read a single captured SSH stdout file on the Chromebook. It requires
completion markers, one matching READY, one non-overflow summary, all
contiguous records and bounded read counts/offsets. It records actual read
requests and seek replies, without assuming a particular libc strategy or
classifying SDK negative reply codes as POSIX errors. It rejects malformed,
partial, duplicate and overflowed logs. Ten synthetic parser cases pass
(0.030 seconds); their successful text is not a native trace.

## Frozen ready archive

nbt-large-body-ready.tar.gz is 38743 bytes, SHA-256
5c2df06c327415b56ff35d5dae81136a4338da61a8de60bf350259ae64446f97.
Its 25 ordinary payload/checksum files include the exact reviewed pair,
source/tests, runner, local checker, audit and pins. Every archived payload
matches its embedded checksum, the member set is exact and shell syntax
passes. No SDK output, BMW binary, actual manifest or plugin payload is
included. Distributed binaries remain outside GitHub. See the
[ready instructions](../tools/larger-body-rehearsal/ready-instructions.md).

No further Ubuntu rebuild is required. Next store/verify this archive on
the Chromebook; a later session must verify separate RAM read-backs and
both help-only startup/normal exits before the 586-byte dummy trial. The
active run should capture stdout with tee/pipefail and assess the complete
trace locally. No new vehicle command is performed by this review.

The old 23-byte tools/packages, milestone-7 source and hidden candidate
stages are unchanged. Native 586-byte behavior, other lengths/seek cases,
open handles across provider death, XML admission, resource lifetime and
HMI guard/fault containment remain unverified. Actual plugin loading and
HMI activation/restart trials remain paused; live RPM is unverified.

## Subsequent vehicle result — 26 November

The owner subsequently completed both RAM read-backs, help-only startup and
the [586-byte dummy run](2026-11-26-larger-body-vehicle-results.md). Exact
stdio reading, normal expiry/cleanup and complete trace assessment passed.
This supersedes the not-yet-run status above for this specific pair/run;
other lengths, open-handle death and XML/HMI integration remain unverified.
The frozen archive and build-review metadata have not changed.
