# Supervisor r2: QNX build review and Chromebook bundle — 26 November 2026

The owner completed all **50 Linux host checks with zero skips/failures** on
Ubuntu in 43.241 seconds, including the namespace/chroot scenarios unavailable
in the cloud. No ARM executable was run. The supplied build archive is 94344
bytes, SHA-256 caaa9f25d812aced7d2754c22f3d5abff7c4d64c380a495f0ac29a441a4a07eb.
Its exact 47-member set is ordinary files/directories; all 24 preparation pins
match the frozen prep and all five recorded build hashes pass. The console
paste agrees with the archive's tests and hashes.

## Executable and imports

| Field | Result |
| --- | --- |
| File | nbt_held_supervisor |
| Bytes | 27292 |
| SHA-256 | 1b499e82eb1ef73b40b327fe7bd334206fc1d21713271c55d363defc11256a28 |
| ELF | ELF32 little-endian ARM ET_EXEC, flags 0x5000002 |
| Entry | 0x100d68 |
| Interpreter | /usr/lib/ldqnx.so.2 |
| Needed | libc.so.3 only |
| Required dynamic function imports | 50; all exported by captured car libc |
| Dynamic relocations | 52 R_ARM_JUMP_SLOT; one R_ARM_COPY |
| COPY | errno, four bytes; matches provider |

There are 25 new required function names versus the held reader, all available
in the captured libc. Only frame_dummy and __do_global_dtors_aux populate
init/fini arrays, with the ordinary optional frame-info imports. No TEXTREL,
RPATH/RUNPATH, C++ stream initialization or host-test markers appear. Host
fault and uninterruptible-output variants are absent. Internal arithmetic
helpers are linked locally. See the [audit metadata](../tools/held-expiry-supervisor/audit-build-2026-11-26.json).

## SDK and actual compiled checks

The new API object exposes timer_t, sig_atomic_t, off_t and pid_t as four bytes;
sigevent and itimerspec are 16 bytes. sigev_notify is offset 0 and sigev_signo
is offset 4. SIGEV_SIGNAL=1, SIGKILL=9, SIGALRM=14 and QNX WNOHANG=64 agree
with the new macro capture. Manual timer initialization matches SIGEV_SIGNAL_INIT.
This establishes the build's ABI/constants, not kernel timer acceptance.

Seventy-six exact instruction sites and surrounding paths were checked:

- The clock-error latch precedes further reads; last-good comparison and
  latching backwards movement are present.
- Both timer handlers preserve interrupted errno and saturate counts before
  addition. The compiled event initialization stores notify/signo at the
  captured offsets and arms the timer through actual libc calls.
- waitpid uses the exact owned child, QNX WNOHANG=64, bounded EINTR retries,
  ECHILD=10 handling, and distinct collected/lost/error paths. Unknown errors
  retain ownership; unowned PIDs are refused by the signal helper.
- The full raw provider control tail and empty stderr precede CONTROL_TRACE_OK.
  Reader captures are refreshed, then the deadline and ownership are checked
  again before SIGUSR1=16 and RELEASE_SENT.
- The launcher's 30000 ms timer precedes its fork. The supervisor arms its own
  31000 ms SIGKILL timer and 25000 ms repeating trial timer. Launcher signal
  forwarding names only its owned supervisor, and real child status is propagated.
- The final write checks deadline after positive progress, and output failure
  or unverifiable clock timing selects nonzero status. Cleanup and record order
  remain before final buffered output; the launcher exit remains authoritative.

Source, SDK and compiled-flow review passes. Runtime SIGKILL timer acceptance,
process/timer inheritance, zombie retention and signal interruption on QNX
remain unverified. No new native timer or held-reader result is inferred.
No further Ubuntu rebuild is needed for this frozen executable.

## Chromebook capture and frozen ready archive

The new [client helper](../tools/held-expiry-client/README.md) verifies all local
pins and independent RAM read-backs, runs help-only startup checks, and only
then permits an explicit normal-expiry trial. Transfers use only fixed flat
/dev/shmem filenames; existing content is never overwritten, and reuse needs
an exact read-back. There is no HMI/plugin-root operation.

A wrapper records the launcher's actual exit status in one final trailer.
The client retains raw stdout, strips only that exact trailer into the
contract capture, and requires **gate ACCEPT, launcher exit 0, SSH/QNET exit 0
and status agreement**. Partial capture, disconnection, nonzero status, bad
trailer, bounds failure and timeout cannot be accepted. Actual on/SSH status
behavior remains a native observation to obtain; discrepancy fails the trial.

Fourteen synthetic/mocked-network host tests passed in 0.113 seconds, then
passed in the extracted ready layout in 0.111 seconds. They cover transported
status failures even with a PASS body, malformed/truncated trailers, byte
preservation, local/RAM pin failures, no-action help and timeout evidence.
No SSH connection or ARM code was used in cloud checks.

- Archive: nbt-held-expiry-ready.tar.gz
- Size: 49982 bytes
- SHA-256: `c8910f1e95a4797588352822dab569678575b46f5804856df0f612bebea1b6df`
- Payload/checksum files: 13; exact member/data/hash checks passed.

The bundle includes only the three own reviewed executables, client/gate/
assessor sources, proposed contract, a labelled synthetic fixture, metadata
and checksums. It contains no car libraries, SDK preprocessing, firmware,
manifest or plugin payload. Binaries remain outside GitHub. Prior endpoint
and held-reader hashes are unchanged. The supervisor's fixed RAM filename is
/dev/shmem/nbt_held_supervisor_1b499e82eb1e.

The first native actions must be RAM read-backs and help-only startup. Any
later trial is this bounded C-only dummy normal-expiry case. Save the entire
new client result directory and reject anomalies without editing/retrying
for PASS. No native result is recorded by this build review. Actual plugin/
HMI loading and activation/restarts remain paused; live RPM is unverified.
