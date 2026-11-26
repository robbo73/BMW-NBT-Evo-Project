# Supervisor r2: adopted source and Ubuntu preparation — 26 November 2026

Claude's r2 upload addresses the previous guardian and child-ownership design,
checks the full control trace before release, preserves raw bytes, and adds a
launcher status plus offline acceptance gate. The original ZIP is 37300 bytes,
SHA-256 2195b1b05cc3e7e044f0f5d756f637859159d5d959f2ec01a6b38f23770d8c44.
All nine payload checksums and the loose architecture match.

The original suite ran here: **30 passed, 16 skipped** of 46, in 13.127 seconds.
Namespace/chroot is unavailable here, so the external 46-pass report remains
separate evidence. The original four issues have concrete fixes in r2; the
launcher owns the supervisor and the reader remains the supervisor's child.

## Local follow-up fixes

Four additional fault tests failed against the upload: clock recovery could
re-enable a deadline check after a failure, backwards movement after the last
good sample was accepted if still after startup, timer handler queries could
clobber errno, and an injected INT_MAX overrun wrapped the counter negative.
The [adopted source and review](../tools/held-expiry-supervisor/REVIEW.md)
fix these with sticky failure, last-good tracking, errno preservation and
saturating updates. New hooks/regressions are host-only. The active assessor,
contract, reader and endpoint remain unchanged. The gate is unchanged from
Claude r2 and requires actual controller exit 0 plus assessor PASS.

After fixes: **34 passed, 16 skipped** of 50, in 13.926 seconds. The complete
standalone dependency snapshot was also tested through its own count-recording
runner, with the same 34/16 result. Original source fingerprints and all
reported/local distinctions are in [PROVENANCE.json](../tools/held-expiry-supervisor/PROVENANCE.json).
No namespace result, ARM execution or QNX compatibility is inferred.

## Frozen Ubuntu preparation

- Archive: nbt-supervisor-r2-prep.tar.gz
- Size: 57032 bytes
- SHA-256: `de8b81b7adab4c72292fc9b51345f386d3beccef8103e20888d03710c071e2c3`
- Exact ordinary payload/checksum files: 25; archived bytes and hashes checked.
- New supervisor source SHA-256: a795030d451a150bb86dbbf02ac4fd27f9558921fc4624b16506c5eb04fb9aaa.
- Output requested from Ubuntu: /home/rob/nbt-supervisor-r2-review.tar.gz.

The package snapshots seven unchanged test dependency files under their
expected relative paths. build_review.sh validates all pins, records actual
host pass/skip counts, cross-builds only the supervisor with the existing
GCC 4.9.4 QNX ARM image, and preprocesses/compiles a separate SDK API capture.
It records ELF/import/relocation/symbol/hash data. It executes no ARM code,
contacts no car and edits no milestone-7 file or frozen candidate/package.
Existing build/review outputs are refused, never overwritten.

QNX timer_getoverrun is declared in the previously captured SDK and exported
by the captured actual libc. The current manual SIGEV_SIGNAL initialization
agrees with the captured macro's notify/signo assignments. SDK ABI and actual
compiled code still require new inspection. SIGKILL timer acceptance, signal
interruption and process/timer inheritance on the car remain unverified.
No native timer experiment or held-descriptor trial is requested by this
preparation. Startup diagnostics before a timer is armed are not a demonstrated
bounded transport path; provider/reader have not started on those refusals.

The next step is the Ubuntu offline build/review archive, followed by compiled
and SDK inspection and a reviewed status-preserving capture wrapper. No
vehicle-ready supervisor package exists. Plugin/HMI trials remain paused and
live RPM is unverified.
