# Native 586-byte dummy-body results — 26 November 2026

Source: owner-pasted Chromebook/BMW output, following separate RAM read-back
and help-only startup checks. No cloud connection to the car was used.
The owner retained the original SSH stdout capture at
`/home/robbo73/bmw-idrive/nbt-large-run.zApvrp`.

The [transcript excerpt](evidence/2026-11-26-large-body-586-owner-transcript.txt)
is transcribed from the pasted output, from READY through the remote final
PASS. Chat transport line escapes are removed; it is not a downloaded or
byte-authenticated copy of the original capture. The package checksum
preamble and subsequent local JSON assessment are described below rather
than included in that excerpt.

## Identity and startup

The owner reported every ready-package checksum passing, including separate
runner and trace-checker pins. The frozen archive remains the reviewed
38743-byte `nbt-large-body-ready.tar.gz`, SHA-256
`5c2df06c327415b56ff35d5dae81136a4338da61a8de60bf350259ae64446f97`.
See the [build review](2026-11-25-larger-body-build-review.md).

Both executables had independent RAM read-backs matching their local pins:

| Executable | SHA-256 |
| --- | --- |
| nbt_large_endpoint_586 (15898 bytes) | 8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2 |
| nbt_large_reader_586 (10248 bytes) | f0d391701c69a8dd07c203c876bbed1ef5d1a885604667b4ed64502f87745884 |

The local temporary read-back path was
`/home/robbo73/bmw-idrive/nbt-large-readback.YAZvdM`, reused sequentially.
The fixed OMAP RAM executables were
`/dev/shmem/nbt_large_endpoint_586_8f502b6394a0` and
`/dev/shmem/nbt_large_reader_586_f0d391701c69`.
Both help-only executions identified the expected revision/586-byte length
and exited 0. SSH authentication retries succeeded before execution.

## Active read, expiry and cleanup

Helper PID 4317301 served `/dev/nbt_large_endpoint_586.4317301` through the
isolated dummy-body.bin RAM alias. The reader reported the complete checked
seek-end/length/rewind/read/close sequence and exited 0. The reviewed success
path requires ftell==586, one complete fread item, an exact comparison of
all binary bytes including embedded NULs, and successful close.

The endpoint emitted four records with zero dropped events and no overflow:

| Index | Request | Offset before → after | Result |
| --- | --- | --- | --- |
| 0 | SEEK_END, offset 0 | 0 → 586 | SDK reply code -1 |
| 1 | SEEK_CUR, offset 0 | 586 → 586 | SDK reply code -1 |
| 2 | SEEK_SET, offset 0 | 586 → 0 | SDK reply code -1 |
| 3 | Read 1024 bytes, xtype 0 | 0 → 586 | 586 bytes, SDK reply code -1 |

This records libc's actual endpoint requests for this run, including its
1024-byte buffered read request for the 586-byte fread item. The seek
return values are resource-manager reply codes, not failed POSIX return
values. These records do not establish the strategy at other lengths.

The helper reported elapsed_ms=10020 for its measured setup/serve/cleanup
interval, then deadline detachment and exit 0. This is its own monotonic
measurement, not an independent wall-clock measurement or a hard ten-second
upper bound. The alias remained a symlink while its followed target was
unavailable. The owned alias and fixture directory were then removed.
No watchdog fallback appeared. The helper PID is not the fixture shell PID.

## Trace assessment and scope

The owner's local checker reported four events, three seeks, one read,
586 returned bytes, no read-error records, and:

```text
PASS: complete 586-byte trace and runner result
```

Codex also ran the unchanged checker against the transcribed excerpt and
obtained the same assessment. This is validation of the supplied trace,
not another native execution or independent recovery of the original file.
The reader had closed before provider expiry.

The 586-byte body size matches the initialization-check manifest's length,
but the served contents were generated dummy binary data. This test did not
serve or parse XML, access real plugin roots, load a BMW framework/plugin,
issue RPM requests, modify hidden candidate stages or request an HMI restart.
The transcript does not independently establish screen stability or exclude
all later unit restarts.

Native bodies above 586 bytes, replies above 2048 bytes, other seek/error
cases, a stalled reader's alarm, and provider death with an already-open
client handle remain unverified. Endpoint disappearance does not unload or
stop code already loaded into HMI. Earlier framework-related restarts remain
unresolved; actual plugin loading and HMI activation/restart trials remain
paused. Live RPM is unverified.

No further BMW command is needed for this checkpoint. Next work is offline
preparation/review of larger-body boundary cases and a separate bounded
open-handle/provider-death test with buffering controlled.
