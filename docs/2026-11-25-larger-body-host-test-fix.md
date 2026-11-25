# Larger-body host read-injection correction — 25 November 2026

The owner's original preparation hashes passed, and the 586-byte normal
host reader and 8193-byte host read passed. Two deliberately injected read
faults unexpectedly returned the normal reader success marker:

| Host test | Expected | Owner output |
| --- | --- | --- |
| blocked read alarm | process terminated by SIGALRM (-14) | exit 0, reader PASS |
| injected read failure | exit 1, no PASS | exit 0, reader PASS |

The 34-test run ended with two failures in 1.556 seconds. The build script
correctly stopped before its Docker compile loop; no new QNX executable
was built and no ARM/BMW execution occurred. The failed output and
build-qnx/host-tests.txt can remain in ~/nbt-large-body-prep/.

## Reproduced cause and bounded fix

A host object compiled with _FORTIFY_SOURCE=2 imports __fread_chk rather
than fread. The initial GNU linker wrappers intercepted fread only. The
same two failures were reproduced with this fortified host default: neither
read failure nor deliberate pause reached its intended wrapper, so ordinary
successful IO continued. This exactly matches the supplied symptom. The
owner's exact compiler/header configuration was not directly inspected.

The host-only fault source now intercepts both fread and __fread_chk.
Both share fault injection, with an explicit marker identifying the hook.
When no fault is selected, each forwards to its corresponding real libc
entry point; fortification is not bypassed. The deliberate blocked path
loops in pause until the actual reader alarm terminates the process, rather
than accidentally resuming after an unrelated handled signal.

A third host reader binary explicitly enables _FORTIFY_SOURCE=2. Two new
regressions require successful unmodified reading, injected read failure,
actual SIGALRM termination and the fortified hook marker. No assertion is
relaxed and no test is skipped. Existing tests also require the read hook
marker when those read faults are selected.

All six target source/header files (large_body.c/.h, trace_log.c/.h,
nbt_large_endpoint.c and nbt_large_reader.c) were checked byte-for-byte
against the original pinned preparation archive and are unchanged. The
build recipe's only change is the new review archive filename; the QNX
compiler arguments and source list are identical. Host wrappers are never
in that target source list. This fixes the test instrumentation, without
claiming a new native runtime result.

## Verification

- The original two failing cases now pass with fortified host defaults
  (two tests, 5.446 seconds).
- All 15 reader cases pass, including the two new fortified regressions.
- The full suite passes: **36 tests in 12.442 seconds** (six body, six
  callback/trace, nine loop and 15 reader tests).
- Bash syntax, the corrected archive's exact file set and every embedded
  checksum pass. The six target file hashes and unchanged compile recipe
  were compared directly with the original frozen archive.

These are host checks, not QNX IPC/ABI, native alarm or larger-body vehicle
results. The earlier native 23-byte results remain separate and unchanged.

## Replacement Ubuntu preparation

| Item | Identity |
| --- | --- |
| nbt-large-body-host-fix-prep.tar.gz | 22408 bytes |
| SHA-256 | 61c89d519b25f808308c2938ceae43d4593ecd119dbde69b75ad3b1335442216 |
| Extracted folder | ~/nbt-large-body-host-fix-prep |
| Expected review archive | ~/nbt-large-body-host-fix-review.tar.gz |

This complete replacement preparation has fresh checksums and metadata.
Extract it into its new folder and run bash build_review.sh there. It does
not delete, modify or reuse the old failed build directory. It builds only
the fixed 586-byte endpoint/reader after all 36 checks pass and still never
executes ARM output or contacts the BMW. Upload the newly named review
archive for ELF/import/compiled-code inspection before native use.

No milestone-7 source, frozen 23-byte package, actual manifest or hidden
vehicle stage changed. Actual plugin loading and HMI activation/restart
trials remain paused. Larger-body native behavior and live RPM remain
unverified.
