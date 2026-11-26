# Held-descriptor reader preparation — 26 November 2026

Following the [proposal assessment](2026-11-26-open-handle-expiry-assessment.md),
a separate C-only raw-descriptor reader is now implemented for offline build
review. Its [source and instructions](../tools/open-handle-expiry/README.md)
include 22 passing host checks (6.591 seconds). No QNX build or ARM execution
was performed in the cloud. A vehicle controller and complete trace assessor
are deliberately not included at this stage; they require the compiled
reader/interface review before a target-ready trial is prepared.

The reader checks the fixed owned dummy alias and expected provider target,
reads/compares 100 bytes, checks offset 100, blocks SIGUSR1 before HELD and
uses sigwaitinfo with a parent-sender check. A release arriving between the
complete HELD marker and wait is retained. Setup/hold/probe alarms and a
rounded whole-reader budget remain explicit. It records each raw read/seek
and close result; unexpected success stops later probes. Its normal OBSERVED
result is not a trial PASS or proof of provider death.

Linux tests use separate ordinary-file fixtures, wrappers injecting descriptor
errors, private fixed-path substitutions and one-second alarms. Pending/missing
release, wrong sender, stalled operations/output, partial/EINTR/broken output,
inherited alarm mask, unexpected success, bad identity/path/content cases and
close errors are exercised. They do not emulate QNX resource-manager behavior.

All 16 proposed API exports spot-checked are available in the captured actual
car libc; captured SDK declarations include sigwaitinfo and raw lseek. This is
not the final required-import/ABI check. The Ubuntu script will cross-build
only the new reader and separately preprocess/compile hold_api.c, exposing
actual SDK sizes/offsets/types without ARM execution. Preprocessed SDK input
and objects stay private; only own source/metadata are committed here.

## Frozen preparation archive

- File: nbt-open-handle-reader-prep.tar.gz
- Size: 12814 bytes
- SHA-256: `a14fb8a469aa53d0f1e6b0e3e4fb60b017da5b97be8b51affb3590ac731f98e2`
- Payload: 11 ordinary files including checksums; exact archive member/payload checks passed.
- Review output on Ubuntu: /home/rob/nbt-open-handle-reader-review.tar.gz

The existing endpoint binary and frozen 586-byte ready package are unchanged,
and neither is included/rebuilt. The copied body sources match the tested
larger-body tool exactly. The script refuses existing outputs, checks all
source hashes, runs host checks before Docker, records ELF/relocation/symbol
metadata and creates the private review archive. It changes no milestone-7
file, contacts no car and executes no ARM code. The new reader must not be
copied to or run on the BMW yet.

After owner build review, complete the controller/readiness/reaping/trace
assessment/whole-trial watchdog protocol and test its failure paths before
preparing any vehicle package. Larger sizes and forced provider death remain
separate work. Actual HMI/plugin trials remain paused and live RPM unverified.

## Subsequent build review

The owner then passed 22 host checks in 6.443 seconds and supplied the QNX
reader and SDK capture. The [compiled review](2026-11-26-open-handle-reader-build-review.md)
passes. This supersedes the not-yet-built status for that reader only; no
native execution or complete controller/assessor exists yet.
