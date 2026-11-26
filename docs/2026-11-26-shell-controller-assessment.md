# Shell controller contribution: review blockers — 26 November 2026

The owner supplied Claude's held-controller-1 shell prototype, tests, original
review and a new held-expiry-assessor.zip. The archive has 11 ordinary files,
36920 bytes, SHA-256
`c2004da484ec9a333585a54e3d43b29b369cc4fef5cdaf91dbb7e5d29c81fdc1`.
All three loose uploads match their archived copies. Original file fingerprints
and observed host results are in the [review evidence](evidence/2026-11-26-shell-controller-review.json).
The [original external review](2026-11-26-claude-controller-original-review.md)
is retained with clear historical attribution.

**Decision: do not adopt this script as the vehicle runner.** It is useful
prototype/test work, but the checks below expose requirements not satisfied
by this implementation. Do not replace the active hardened assessor with the
bundled earlier variant. No new target package or car command follows.

## Supplied host suite reproduced

In a separate private host layout, the uploaded controller/tests/checker were
combined with unchanged copies of our reader, body and raw-fault source.
All **12 test methods passed in 10.294 seconds**, covering 22 stand-in scenario
executions across dash and bash plus static/help/preflight checks. The original
review's four repeated runs are externally reported, not repeated here.

The reader is compiled for Linux with substituted paths; the provider is a
shell stub with canned traces and a shortened lease. Post-release errors are
injected. The suite uses the uploaded legacy checker, not our later amended
50-test checker. Passing it does not establish QNX shell/runtime behavior,
complete capture integrity or a complete watchdog bound.

## Blockers and independent counterexamples

### 1. Target printf is already known missing

The script preflights printf at line 44 and uses it for protocol/section output
at lines 82 and 171. Earlier owner-pasted OMAP results in this session showed
`/bin/sh: printf: cannot execute - No such file or directory`.
That is an existing negative result, not an unanswered availability question.
As written, its preflight would refuse to proceed in that observed shell.
Replacing printf with echo alone would not solve the other blockers below.
No new car test is needed to rediscover this.

### 2. Old contract and release under an invalid control

This contribution is based on cb4c8c0, before c840c76 added the mandatory
CONTROL_TRACE_OK gate and retained watchdog coverage through framed output
and cleanup. This script has no full pre-release trace validation and cancels
its watchdog before both operations. The bundled checker also lacks the later
numeric canonicalization/SDK-width checks. Copying it over the active checker
would discard reviewed requirements.

A separate synthetic experiment changed only the stand-in provider's trace
from requested=100 to requested=101, leaving the real host reader's controls
and provider DETACHED line intact. The controller still **sent RELEASE_SENT
and exited 0**. Its legacy checker then returned PREREQUISITE_FAILED; the
active amended checker, evaluated with private host path substitutions,
returned CONTRADICTORY with missing CONTROL_TRACE_OK, premature release,
control-trace mismatch and ordering findings.

Post-hoc rejection works, but the required pre-release gate is absent. The
controller must validate the exact complete trace and empty provider stderr
before authorizing the probe sequence.

### 3. Watchdog does not bound blocked controller output

The first BEGIN is written before the watchdog is created. With an already
full stdout pipe and the private host watchdog shortened to one second, both
dash and bash controllers were **still running after 2.5 seconds**. No reader
or provider needed to start for this counterexample. The private harness then
killed/reaped its own isolated process group and removed its own fixture.

The signal traps only increment flags; they do not independently terminate a
blocked logging operation. Later cancellation before sections/cleanup leaves
those phases without the nominal whole-trial watchdog as well. Even the
candidate's own stated duration allows 25 seconds plus two five-second reap
grace periods and cleanup. Neither host baseline nor this implementation
establishes a hard 25-second whole-trial bound.

### 4. Line-based framing silently changes raw captured bytes

A synthetic provider was changed to write one NUL byte immediately before its
otherwise normal READY line. Under **both dash and bash**, the controller
sent release, exited 0, and emitted a final framed capture containing no NUL;
the bundled legacy assessor returned **PASS**. Its read/string/printf framing
had removed the byte. Thus the declared counts describe normalized shell
strings, not necessarily the original child stream bytes.

The contract requires verbatim child captures and rejection of non-ASCII
input. The assessor cannot reject corruption that was deleted upstream.
Use bounded byte-oriented capture/framing and reject forbidden bytes without
normalizing them. This was a host counterexample only, not observed car output.

### 5. PID ownership and cleanup remain incomplete

The original review acknowledges shells may reap background children before
an explicit wait. An unreaped-through-script flag therefore does not prove
that the kernel still reserves the PID. Reader release and abort-path kill
can race exit/reuse. Merely checking kill -0 does not close that gap.
Timer processes and parent-death/cancellation behavior also need ownership
review; a stored controller PID is not an unconditional identity guarantee
if the controller exits unexpectedly before its timer.

No reuse incident was observed or induced. This is a concrete design gap;
we do not need to ask the owner to accept it when selecting an implementation.
A native C supervisor can retain exact child statuses and avoid reaping a
child until it no longer needs to signal it, with SIGCHLD dispositions
configured accordingly. Its watchdog/output/cleanup still need separate
proof; translating the shell literally is not sufficient.

## What remains useful

The host build of the real reader exercises direct-parent and signal-sender
checks. The scenario matrix is a useful starting point for a new supervisor.
Separating controller completion from final assessment, recording individual
child streams and preserving diagnostics on failure are also retained goals.
WATCHDOG_FIRED target=none is reasonable as a failure-only schema extension
if a future controller needs it; it does not justify replacing the active
assessor or weakening its mandatory gate. No such extension is applied here.

## Next work and current state

Prepare a C supervisor with exact owned-child handling, raw bounded capture,
complete control validation before release, monotonic whole-trial bounds,
blocked-output handling, bounded cleanup and deliberate watchdog cancellation.
Reuse the scenario concepts and add the counterexamples above as regressions.
Review any new SDK declarations/imports and actual compiled QNX code before
preparing a target package. No new reader or endpoint rebuild is needed for
this review.

The current reader/endpoint, active 50-test assessor, proposed revision-2
contract, frozen packages and hidden stages are unchanged. The shell candidate
and its modified legacy assessor remain private review inputs, outside active
tools. No QNX code or BMW command was executed. Native held-descriptor behavior,
XML/HMI integration and live RPM remain unverified; plugin/HMI trials stay paused.
