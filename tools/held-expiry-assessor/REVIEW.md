# Assessor integration review — 26 November 2026

The owner supplied four loose files and held-expiry-assessor.zip from Claude.
The ZIP contains eight ordinary files; safe member checks passed, and all
four loose uploads match their ZIP copies byte-for-byte. The original upload
is preserved outside the repo; PROVENANCE.json records every original file's
SHA-256 and the archive identity. No supplied document is treated as vehicle
authorization or runtime evidence.

## Independent rerun and findings

All 45 supplied synthetic tests passed in 0.496 seconds, including semantic
mutation/truncation sweeps and the seeded 3000-case corruption test. The
bounded standard-library-only parser, distinct callback/syscall result fields,
fixed framing, identity checks and error/termination rejection are retained.

Two gaps were reproduced against the unchanged upload, with valid section
byte counts rebuilt: events=02, bytes=0586 and count=0100 still produced PASS,
as did three errno values of 2147483648. The former violates the declared
canonical-number grammar; the latter cannot be emitted by the reviewed QNX
signed 32-bit errno. These are input-validation gaps, not observed vehicle
failures or evidence that an actual capture was corrupted.

The adopted parser rejects noncanonical numbers consistently and checks the
SDK-width bounds of syscall result/errno. No particular error number is
required. The new regressions preserve the original synthetic failure tests.

## Controller contract decisions

Require **CONTROL_TRACE_OK provider=P events=2** after provider reaping and
endpoint-absence checks, before RELEASE_SENT. The controller must validate
the complete captured provider stdout/stderr, deadline result and exact
100-byte read/SEEK_CUR trace before printing this claim or sending SIGUSR1.
A post-hoc parser failure is useful but does not justify probing under an
invalid control. The final assessor still validates the actual framed trace.

Move WATCHDOG_CANCELLED after framed child captures and FIXTURE_CLEANED, so
the proposed record order no longer implies coverage ended before those
operations. An event alone is not a watchdog implementation. Its ownership,
controller IO, deadlines, cleanup/reaping and cancellation races still need
source and host testing. The current log has no whole-trial timestamp and
cannot independently establish a 25-second total duration.

C is defined as the direct-parent controller process, not necessarily a shell.
A C controller can count captured bytes itself and normalize waitpid statuses;
there is no requirement to discover a shell wc utility. Its implementation
must retain bounded child-output capture and preserve exact stream bytes.
No controller is implemented or authorized for target execution by this note.

The wire contract remains held-expiry-log/1 because it has never been
implemented or released to a vehicle; PROPOSAL_REVISION=2 identifies the local
amendments. Original synthetic samples missing the new gate intentionally
fail the adopted checker. Checked-in synthetic examples are regenerated from
the amended test builder. The historical INTEGRATION-NOTE is attributed as
an account of the original proposal, not a current contract override.

## Verification and remaining scope

All **50 synthetic tests pass in 0.532 seconds**. Five added test methods cover
noncanonical provider fields, errno beyond SDK width, absent/premature trace
gate, gate identity/count, and early watchdog cancellation. Existing mutation
sweeps run against the amended format. No network/process module is imported
by the assessor; no car connection or QNX execution is involved.

The reader remains SHA-256
9a54c7f4dba539d25861f6e98a018d778bec62eb86462b7b208138a4be34de79;
the endpoint remains
8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2.
No native held-handle result exists. Next implement/test the controller to
this reviewed proposed contract, then cross-build/inspect its actual QNX
behavior before creating any vehicle-ready package. Plugin/HMI trials
remain paused and live RPM is unverified.
