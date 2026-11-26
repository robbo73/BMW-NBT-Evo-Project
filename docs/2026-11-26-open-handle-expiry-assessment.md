# Open-handle expiry proposal: integration assessment — 26 November 2026

Reviewed against commit 4ef1c50's larger-body endpoint, stdio reader, runner
and the owner-supplied native 586-byte result. The [external proposal](2026-11-26-open-handle-expiry-test-proposal.md)
is retained with attribution and an original-upload hash. No implementation,
new cross-build, package or car command is supplied by this review.

## Accepted direction

Reuse the exact tested 586-byte endpoint and leave its frozen package,
stdio reader and all hidden candidates unchanged. A separate sibling reader
and runner should test an idle open descriptor across normal provider exit.
Keep this separate from larger lengths, forced provider death and HMI work.

A raw descriptor avoids the FILE stream's buffering. Before the hold, one
read of 100 bytes must match the independent expected body prefix; a raw
SEEK_CUR query must report offset 100. Validate the endpoint trace against
these operations. This establishes the actual pre-expiry request path for
this client/run; do not infer post-expiry behavior from it.

The release condition is server wait status 0 after normal deadline exit,
not simply ten seconds elapsed or disappearance of its pathname. Require
path absence independently as well. Once the provider is reaped, bounded
raw read/lseek operations on the still-open descriptor can characterize
client-visible loss. Record close separately; its success does not prove
continued provider availability. Keep errno numeric and record it only
when the operation reports failure, capturing it before logging/clock calls.
No particular errno value is an acceptance prerequisite.

## Corrections and tighter requirements

1. **Buffering evidence:** the existing trace proves a 1024-byte request
   returning 586 bytes for a 586-byte fread item. It does not prove that any
   unused bytes remained buffered after that full item was consumed. It
   supports avoiding stdio for the held-descriptor experiment, but is not
   evidence that the previous reader could return additional cached data.

2. **Current ordering:** the existing runner requires successful reader
   completion before it waits for the helper. This does not make overlap
   with expiry structurally impossible: a stalled reader could still be
   alive at the deadline. It provides no intentional held-handle protocol
   and no successful coverage of that case. A new protocol is required.

3. **Readiness and release:** kill -0 proves process existence, not HELD
   readiness. The new runner must observe a complete readiness marker after
   the checked control operations and before authorizing release. Install
   the signal handling and block the release signal before announcing HELD;
   use a checked sigprocmask/sigsuspend loop to avoid lost-wakeup races.
   A signal handler should only set a volatile sig_atomic_t flag. Define
   failure/cleanup for reader death, missing markers and early signals.

4. **Bounds:** use a short setup alarm, a separate bounded holding phase
   spanning the ten-second lease, and a fresh short alarm per probe/close.
   Eighteen-second hold and three-second probes are design suggestions,
   not validated native settings. A parent wall-clock watchdog around
   25 seconds must cover both children and abort the whole test, rather
   than permitting all phases to consume their separate maxima. Preserve
   which phase/operation was last reached. Native signal interruption of
   a blocked QNX send remains unverified; an alarm alone is not proof of
   containment. Cleanup must not replace a finite watchdog with an
   unbounded wait for a TERM-only child.

5. **Capture:** stderr is not included by the previous SSH-stdout tee
   command. The new runner/capture design must explicitly collect both
   streams. A record must be fully emitted before beginning an operation;
   partial writes/EINTR and blocked output need defined behavior. Merely
   writing to fd 2 is not an unlimited guarantee of marker survival.
   Keep control markers separable from human diagnostics, and validate
   exactly one complete run with consistent child identities and ordering.

6. **Verdicts:** expected descriptor loss requires complete controls,
   confirmed normal server exit before release, completed bounded probes
   reporting failure, and a normally completed reader/cleanup. A zero-byte
   read at verified offset 100, positive bytes or a successful post-exit
   seek is an unexpected result requiring explanation, never a pass.
   Stop after the first anomalous probe result; close/cleanup remain
   bounded. A signal/watchdog termination indicates an incomplete or
   timed-out run, not successful recovery. Missing DETACHED alone is
   insufficient to diagnose a hang; it can also mean setup failure,
   logging failure or an incomplete capture. Classify using the full log
   and child statuses. Check freshness and counts of all markers.

7. **Timing:** 10020 ms is one measured setup/serve/cleanup interval, not
   an expected exact duration. Compare against it descriptively. A longer
   interval alone does not establish that an open binding delayed detach;
   scheduling, tracing and cleanup are other possibilities.

8. **Process ownership:** independent watchdogs/signals must be scoped to
   the exact children while they are still owned, with cancellation/reaping
   on every terminal path. A remembered PID and kill -0 alone cannot prove
   identity indefinitely. Review PID reuse and watchdog cancellation races
   explicitly, rather than copying the old pattern without assessment.

## Documentation boundary

The proposal cites the QNX 6.5.0SP1 resmgr_detach page for ALL versus
PATHNAME detachment, open-binding invalidation, EBADF and waiting for
connection functions. This review could not independently retrieve that
page: the network proxy returned 403. Those quotations remain externally
reported documentation, not newly verified SDK/runtime facts.

The inspected endpoint source does call resmgr_detach with ALL after it
stops its dispatch loop, then frees its context and destroys dispatch.
It does not resume dispatch to serve an invalid-binding error. A test
released only after the process has been reaped measures the combined
normal-detach/process-exit case. It cannot isolate detach-only behavior,
prove every kernel error path, or characterize a request already in flight
at provider death.

## Offline work before another vehicle run

Freeze the readiness/release, timeout, logging and verdict protocol first.
Then implement separate files and meaningful host tests for early/lost
signals, reader/setup failure, normal and abnormal provider exit, missing
or duplicated markers, partial output, probe stalls, unexpected success,
watchdog/cleanup races and no release before the checked prerequisites.
Check actual QNX declarations, return types and ARM off_t/lseek ABI before
cross-building, then compare every required import/relocation with the
captured car runtime and inspect the actual compiled control flow.
A host stub or passing source test is not a QNX execution result.

If a reviewed build is later prepared, vehicle order is RAM read-back,
help-only startup, then one normal-expiry dummy trial. Forced death with
an open client is separate later work. No real manifest, XML parser,
plugin root, framework loading, RPM request or HMI restart is part of this
proposal. Actual plugin/HMI trials remain paused and live RPM is unverified.
