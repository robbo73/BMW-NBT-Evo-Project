# Native held-descriptor expiry results — 26 November 2026

The owner ran the frozen C-only normal-expiry trial on NBT Evo's hu-omap
through Chromebook SSH, then uploaded the complete result directory.
No cloud connection to the car was used. The unchanged assessor and
status-plus-transport gate return **PASS / ACCEPT** on the uploaded bytes.
This is one native normal-expiry result, not a new plugin/HMI or RPM result.

## Evidence and identity

The upload nbt-held-expiry-vehicle-results.tar.gz is 1427 bytes, SHA-256
`e238c8fb96c9115f2a0d7113e27c5859874eddaef0c486a1b218595ad7207c69`.
Its exact four members are one ordinary directory and three ordinary files;
no links or other file types occur. The original Chromebook directory is
/home/robbo73/bmw-idrive/nbt-held-run-g_epknqs. Its client start timestamp is
2026-11-26T07:39:29.901787+00:00 (18:39 AEDT); authentication followed this
stamp, so it is not the exact native trial start or a whole-trial duration.

The committed [evidence directory](evidence/2026-11-26-held-expiry/) preserves:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| [capture.hxc](evidence/2026-11-26-held-expiry/capture.hxc) | 2394 | 88fdf4799b5ff2f7c69a760d310768d85fa92f3a9dfa84ee753d828420b0b37d |
| [ssh.stdout.raw](evidence/2026-11-26-held-expiry/ssh.stdout.raw) | 2426 | a86f93c9bc7cb9316440597c5983be772fe10490f17693415557e768999d6d29 |
| [result.json](evidence/2026-11-26-held-expiry/result.json) | 502 | e6070d6f5e16ce779b4c5237b3d5dfbbcb76646423c2df930115b0d5e71964a7 |

Both capture hashes match the owner's earlier console result and the uploaded
metadata. Raw stdout is exactly capture.hxc plus the single final
`NBT_HELD_LAUNCHER_EXIT status=0` line. The helper recorded SSH exit 0 and
agreement with the shell-observed launcher exit. This is consistency and
integrity checking of supplied evidence, not independent authentication of
its origin or a second vehicle execution.

The preceding owner console shows independent RAM read-backs for all three
reviewed executables and help-only exit 0, repeated immediately before trial:

| Executable | SHA-256 |
| --- | --- |
| nbt_large_endpoint_586 | 8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2 |
| nbt_hold_reader_586 | 9a54c7f4dba539d25861f6e98a018d778bec62eb86462b7b208138a4be34de79 |
| nbt_held_supervisor | 1b499e82eb1ef73b40b327fe7bd334206fc1d21713271c55d363defc11256a28 |

The upload contains captures only, not a second copy of those binaries.
See the [QNX build review](2026-11-26-supervisor-r2-build-review.md) for their
frozen bundle, compiled checks and source-supported sequencing.

## Control, expiry and release

Supervisor PID 4579445 owned provider 4579447 and reader 4583544. The owned
fixture was /ramdisk/mm/.nbt-held-alias-586.4579445/dummy-body.bin, pointing to
/dev/nbt_large_endpoint_586.4579447, outside real plugin roots.

The raw descriptor control read returned 100 matching dummy bytes and its
SEEK_CUR returned offset 100. The provider recorded exactly the expected
requests, with no dropped events or overflow:

| Index | Endpoint request | Offset before → after | Reply |
| --- | --- | --- | --- |
| 0 | READ requested=100, xtype=0 | 0 → 100 | count=100, resource-manager code -1 |
| 1 | SEEK_CUR, offset=0 | 100 → 100 | resource-manager code -1 |

This confirms requested=100 for this native raw read, distinct from the
1024-byte request in the earlier full stdio test. No libc stdio buffering is
used by this held reader. The handle remained at offset 100, before EOF 586.

The provider reports deadline detachment, elapsed_ms=10023, and exit 0.
That is its own measured interval, not an independently measured hard bound.
The controller records HELD, provider reaped with status 0, endpoint absent
and alias dangling, then CONTROL_TRACE_OK before RELEASE_SENT. The reader
reports RELEASED sender=4579445, matching its direct parent. These records
agree with the reviewed source's pre-release checks; causal ordering is not
proved by a parser alone.

## Operations after provider exit

| Reader operation | Syscall result | errno | Reported elapsed_ms |
| --- | --- | --- | --- |
| read64_a | -1 | 9 | 0 |
| seek_start | -1 | 9 | 0 |
| read64_b | -1 | 9 | 0 |
| close | -1 | 9 | 0 |

Each read/seek failed rather than returning cached bytes, zero-byte EOF or
hanging in this trial. A reported 0 ms is the reader's millisecond-resolution
measurement, not zero execution time. Numeric errno is recorded as observed;
acceptance does not require that particular value. Provider reply code -1
above is not a syscall failure. Close also failed; it was not a successful
close and is an explicitly permitted observation in the reviewed contract.

The reader exited 0 after checking all three probe failures and recording
close. Both child stderr sections are empty. The controller records owned
fixture cleanup, watchdog cancellation and END result=complete. Launcher exit
0 appears in the exact final shell trailer and agrees with the helper's
SSH exit 0. No abort/watchdog-firing record appears.

## Offline reassessment and limits

Codex checked the exact member set, sizes, file hashes, trailer/body equality,
and the unchanged frozen client/gate/assessor. The resulting
[offline assessment](evidence/2026-11-26-held-expiry/offline-assessment.json)
is PASS with no findings; the transport gate returns ACCEPT with no reasons.
The active assessor SHA-256 remains
`84be7de262c5d3e982d187869440e5e18364a008ecfdf58f508405408b59b162`.
To reproduce the log assessment and recorded-exit gate from this checkout:

```sh
python3 -B tools/held-expiry-assessor/assess_held_expiry.py \
  --input docs/evidence/2026-11-26-held-expiry/capture.hxc
python3 -B tools/held-expiry-supervisor/gate_trial.py --controller-exit 0 \
  --input docs/evidence/2026-11-26-held-expiry/capture.hxc
```

Here the explicit 0 reproduces the already-recorded trailer/metadata value;
it must never be guessed for a new trial. The unchanged capture helper
extracted that status automatically during the native run.

The successful path supports QNX acceptance of the timers armed by this
build (including the supervisor's self-SIGKILL timer), fork/exec/wait and
normal parent-authenticated release. It does **not** exercise 25/30/31-second
alarm delivery, blocked-output interruption, emergency kills, supervisor or
launcher death, adverse wait/clock paths or general process inheritance.
The log has no independent whole-trial timing. These remain separate native
questions despite host fault-test coverage.

This is normal provider expiry with a raw descriptor open, not forced
provider death, an open FILE* stdio test, a larger body, XML parsing or HMI
integration. It proves no unload of code already mapped into HMI. No screen
stability report accompanies this upload; capture success cannot exclude
all later restarts. Earlier framework-related crashes remain unresolved.
Actual plugin/HMI loading and activation/restart trials stay paused. No RPM
request occurred and live RPM remains unverified.

No repeat car run is needed for this checkpoint. Next work is offline review
of the larger-size boundary cases and remaining recovery requirements,
keeping these distinct from any future HMI initialization trial.
