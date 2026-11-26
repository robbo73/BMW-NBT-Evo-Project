# Supervisor r2 adoption — 26 November 2026

The owner supplied held-expiry-supervisor-r2.zip, 37300 bytes, SHA-256
2195b1b05cc3e7e044f0f5d756f637859159d5d959f2ec01a6b38f23770d8c44.
All nine payload pins match and the loose architecture matches its archived
copy. PROVENANCE.json records the exact original files and external/local
results separately. No supplied document authorizes a vehicle operation.

## Original r2 review

The launcher owns the supervisor until collecting its exact status. The
supervisor remains the reader's direct parent and owns provider/reader PIDs.
This removes the earlier guardian's parent-check-then-kill design. The supplied
late-write and wait-error corrections are retained. The client-side gate requires
both launcher exit 0 and active-assessor PASS; it never authenticates a claimed
status or replaces an actual transport status capture.

The supplied suite ran locally: 46 discovered, **30 passed and 16 namespace
checks skipped**, 13.127 seconds. The external 46-pass namespace result is not
claimed as reproduced. The active dependencies' hashes match.

## Four additional reproduced regressions and local corrections

Before changes, four extra namespace-free tests failed against the exact r2
source:

- A failed clock followed by a successful clock read made trial_expired and
  stopped return false again, despite clock_failed remaining set. read_clock
  now latches failure so later readings cannot re-enable release/deadlines.
- A reading lower than the last successful value but still after start_ms
  was accepted. The per-process last good value is now tracked; regression
  latches failure. Equal readings remain allowed.
- timer_getoverrun failure inside either handler changed errno of the interrupted
  operation. Both handlers now preserve/restore errno around that query and
  counter update. This protects exact waitpid/file error interpretation.
- A synthetic INT_MAX overrun caused signed arithmetic to wrap the timer count
  negative. Both counters now saturate at 1000000 before addition. This is
  injected range testing, not a measured real timer overrun.

Four regressions, the overrun fault hook and reset of the new test clock state
were added. The active assessor, proposed contract, reader and endpoint were
not edited. The gate itself is unchanged from the upload. Production paths,
25/28/30/31-second timings and release order are unchanged.

The adopted suite: **50 discovered, 34 passed, 16 skipped**, 13.926 seconds.
Namespace-free tests execute real Linux launcher processes plus fault units;
other host test variants never enter the QNX build command. No ARM execution
or car connection occurred. Prior source-error probes are fixed; this is not
a claim of native QNX acceptance.

## Ubuntu build review stage

The standalone preparation snapshots only the unchanged dependency files
needed by these tests. run_host_checks.py writes actual pass/skip/error counts;
it refuses to treat fewer than 34 passes as a successful local baseline. A
namespace-capable Ubuntu host may run all 50; namespace skips stay explicit.

build_review.sh verifies all standalone payload hashes, runs host checks,
cross-builds only nbt_held_supervisor, and preprocesses/compiles supervisor_api.c.
It captures ABI object sizes/offsets, timer macros, ELF metadata, relocations,
imports and hashes. It never runs ARM code. Existing build/archive output is
refused; errors must be shared rather than bypassed. No toolchain installation
or rebuild of existing binaries is requested.

The review archive contains vendor SDK preprocessing privately for ABI inspection;
those files and compiled objects/binaries must not be committed to GitHub.
The current repo preserves own source/tests/provenance only.

## Limits still requiring review

QNX declarations/compiled output and the actual required imports are not yet
inspected. SIGKILL timer acceptance, timer_getoverrun handler behavior, process
and timer inheritance, zombie retention, and EINTR behavior on the head unit
remain unverified. timer_getoverrun is declared in the captured SDK and its
symbol is exported by the captured car libc; that is a feasibility check only.
Startup diagnostics before a kernel timer can be armed are not a demonstrated
bounded transport path. Default/help and refusal paths start no provider/reader.

The whole-trial capture must retain the launcher's actual exit status (including
transport failure) and feed it to gate_trial.py; a manually invented 0 is not
evidence. No vehicle runner/capture wrapper or target-ready package is supplied.
No plugin, XML, RPM request or HMI operation is involved. Those trials remain
paused and live RPM is unverified.
