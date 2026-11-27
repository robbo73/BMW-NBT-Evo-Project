# CDS-to-ShiftDeck Ubuntu host results — 27 November 2026

The owner completed the frozen [host-only preparation](2026-11-27-shiftdeck-integration-assessment.md)
on Ubuntu, reported all checks passing, and uploaded the complete result archive.
Inspection confirms the source pins, test log, compiler and deterministic replay
agree. No uploaded executable was run during this review. No BMW/QNX connection,
native build or milestone-7 edit was part of this preparation.

## Identity and source consistency

- Upload: nbt-cds-shift-host.yqNr1I.tar.gz, **34504 bytes**.
- SHA-256: `315817d8ed7000a02e9fe76cd8eb9b3267d355f6b545c0b39f39567436083595`.
- Exact archive members: one ordinary directory and seven ordinary files; no
  links, special members, duplicate names or unexpected paths.
- Recorded working output: /home/rob/nbt-cds-shift-host.yqNr1I.
- SOURCE-SHA256SUMS equals the frozen preparation's manifest byte-for-byte;
  all **12 source/document pins** match the retained preparation files.
- PROVENANCE.json equals the frozen copy, including upstream commit
  8567abaadd1305965b3ad39e3222575cd49c507d and the three unchanged method hashes.

The supplied compiler is **g++ 9.4.0**, Ubuntu 9.4.0-1ubuntu1~20.04.2.
The original log lists each of the **24 tests as ok**, followed by:

```text
Ran 24 tests in 0.240s

OK
```

These are owner-run Linux tests against synthetic fixtures and the fake image
sink. They are not new native firmware/ABI observations or independent build
attestation. No rerun was needed to inspect this supplied result.

## Saved deterministic replay

The [unaltered demo.json](evidence/2026-11-27-cds-shift-ubuntu/demo.json) is
2672 bytes, SHA-256
`56f87eda4de4e08a8d4ebd0457f6c35c1d338cc0faef27e8dd8155a2abf53d7c`.
It matches the uploaded RESULT.json hash and is **byte-identical** to the
previous cloud execution from the same frozen package.

Independent interpretation of the emitted digit-image IDs gives:

| Synthetic fixture step | RPM display from model IDs | Receipt behavior |
| --- | --- | --- |
| Initial poll at 1000 ms | -- | No receipt |
| JSON RPMSpeed=700 received/polled at 1100 ms | 700 | Sequence 1, time 1100 |
| Error 402 at 1200 ms, then poll | 700 | Rejected; still sequence 1/time 1100 |
| Poll at 1850 ms | -- | Exactly 750 ms old; no restamping |
| JSON RPMSpeed=0 at 2000 ms | 0 | Valid receipt, sequence 2 |
| Stop, then late callback at 2100 ms | -- | Update rejected while latch remains alive |

Speed remains unavailable (--). All replay observations retain
producer_freshness_verified=false. These model IDs do not show rendered
pixels, real image resources, screen geometry or native HMI dispatch.
The 750 ms boundary is the pinned upstream baseline exercised by the test,
not a measured or selected production CDS cadence.

## Host executable and retained evidence

The uploaded host-replay is **88544 bytes**, SHA-256
`e684138c48153e28d743d9ca5a388d40ead4d6f70aa781439a612207c61bff6b`.
Its ELF header identifies **64-bit little-endian x86-64**, not the QNX ARM
target. The binary is retained privately with the original upload, outside
Git; it was inspected as data and is not a BMW payload.

The [evidence directory](evidence/2026-11-27-cds-shift-ubuntu/) preserves the
six original non-executable report files, a new inspection audit and checksums.
No source parser, renderer, native candidate or frozen package was changed to
obtain this result. The helper's RESULT.json flags no vehicle connection,
native execution or milestone-7 edit, consistent with its reviewed script.

## Implication and next step

This validates the isolated receipt-latch/model-update experiment on the
owner's Ubuntu toolchain as well as in cloud. It supports reuse of the tested
ShiftDeck drawing logic once an appropriate native input/lifecycle is proven.
It does not test the production UTF-16 parser/callback, establish producer
freshness, prove unsubscribe/quiescence or fix the earlier runtime crashes.
Native plugin initialization, actual screen rendering, CDS permissions/cadence,
second-app behavior and adapter-free live B58 RPM remain unverified.

No repeat host test or rebuild is required now. The next connected-car work
remains the read-only collection of eight runtime libraries for the separate
[loading-context investigation](2026-11-26-runtime-context-review.md), copied
from BMW to Chromebook. Actual library/HMI loading stays paused. Existing
milestone-7 source, Android Auto functionality and hidden stages are preserved.
