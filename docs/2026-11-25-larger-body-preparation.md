# Bounded larger-body preparation — 25 November 2026

The owner returned to Ubuntu after the independent larger-body review and
[integration assessment](2026-11-25-larger-body-endpoint-assessment.md).
A separate [C-only preparation](../tools/larger-body-rehearsal/README.md)
is now ready. It does not modify any frozen 23-byte tool or milestone-7 file.

## Concrete implementation

- A compile-time body length defaults to 586 and is capped at 16384. The
  position-dependent binary pattern includes NULs and block offsets. Its
  actual array length drives both stat size and slicing. Expected bytes are
  independently checked in Python using a different formatting algorithm.
- The new endpoint retains readonly/mutation refusal, the ten-second lease,
  100 ms receive timeout, corrected receive-ID classification, incoming
  msg_max_size 2048 and nparts_max 2. It does not infer an outgoing byte cap.
- Read instrumentation captures incoming fields, actual bounded count,
  before/after OCB offsets and result. A new seek wrapper snapshots original
  unsigned offset bits/whence, calls the actual SDK default, then records
  the result/offset without altering the default reply or OCB.
- A fixed 64-record trace preserves its first entries and reports saturated
  dropped count/overflow. It prints once after detachment/destruction with
  monotonic elapsed time, not inside handlers. Logging has bounded overhead;
  SIGKILL cannot flush it. A future native profile must distinguish a correct
  read from a complete trace and require no overflow for completeness.
- A separate bounded reader checks link/type/size, both fseeks, nonnegative
  exact ftell, one full fread item, every binary byte and fclose under its
  own five-second alarm. It accepts only a canonical shell PID for a fixed
  dummy alias path, not arbitrary paths or a real manifest.

The new fixed endpoint namespace is
/dev/nbt_large_endpoint_586.<pid>. The prospective reader alias is
/ramdisk/mm/.nbt-large-alias-586.<shell-pid>/dummy-body.bin. Neither is
inside a real plugin root, and no active alias runner is supplied yet.

## Offline checks completed

All 34 tests passed together in 7.397 seconds:

| Group | Count | Scope |
| --- | --- | --- |
| Binary body/bounds | 6 | Twelve lengths: 1,23,586,2047,2048,2049,4095,4096,4097,8192,8193,16384; exact bytes, partial reads, length-derived edges, seeded random offsets, masks/nulls and compile-time cap refusal |
| Callback/trace | 6 | Actual static read/seek callbacks with host probes at 586/2049/8193; status/IOV/count/OCB agreement, error paths, exact default seek forwarding and bounded log overflow |
| Receive loop | 9 | The prior non-null timeout context/negative receive-ID contract, pulses, stale errno, retry and fatal receive/handler behavior in the new loop |
| Reader | 13 | Host full reads at 586 and 8193, exact/wrong data, canonical PID/overflow and link/type controls, six stdio errors and own-alarm termination of a blocked read |

The fake seek default deliberately overwrites its input union and supplies
synthetic negative/zero/positive reply codes. Those tests validate wrapper
preservation, not QNX seek semantics. All host stubs/fault wrappers stay out
of the QNX build command. No namespace/IPC, ARM ABI or HMI is emulated.

A private 32-bit declaration-only check against the exact captured QNX 6.5
SDK passed, including lseek callback assignment and captured whence/offset/
union/OCB layout checks. Vendor preprocessing/types remain private. The
[design note](../tools/larger-body-rehearsal/DESIGN.md) records its hash and
scope. It is not a QNX executable or a runtime/ABI validation.

The actual car libc already exports iofunc_lseek_default, but that direct
symbol is new relative to the old helper. Both new executables must undergo
fresh ELF/import/startup/compiled-callback review after the owner's build.

## Ubuntu deliverable

nbt-large-body-prep.tar.gz contains 19 ordinary source/document/metadata/
checksum files (plus directories), no ARM executable, SDK output, BMW file,
manifest or payload. Every archived file matches its embedded SHA256SUMS.
The build script passed Bash syntax checking.

| Item | Identity |
| --- | --- |
| Preparation archive | 20985 bytes; SHA-256 8dea68a78e86da702341da7c2ec2a3abf1cfd2bc9dfa10467814ded792631695 |
| Expected 586-byte dummy body | SHA-256 3218a4ee930711ef93fbdc6272ba60a086eaa2b4f6f9b803f6d5c80d2240716f; generated host expectation, not a native read-back |

On Ubuntu run bash build_review.sh from the fresh extracted directory. It
verifies hashes and host checks, then uses the existing QNX ARM C image to
build only nbt_large_endpoint_586 and nbt_large_reader_586 in a separate
build-qnx directory. It mounts only this preparation directory, refuses
existing outputs/review archives and collects ELF metadata/symbols/hashes.
Upload /home/rob/nbt-large-body-review.tar.gz for inspection. It never runs
ARM output, contacts the car or edits milestone-7.

No native 586-byte or larger-body result is claimed. Raw seek matrices,
open handles across provider death, client buffering controls for those
cases, actual XML parsing/admission, HMI guard lifetime and the previous
runtime/restart failures remain unverified. Actual plugin loading and HMI
activation/restart trials remain paused; live RPM is unverified.
