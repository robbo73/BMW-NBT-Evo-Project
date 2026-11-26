# Held-expiry assessor contribution — 26 November 2026

The owner provided Claude's offline assessor, proposed contract, integration
note and synthetic examples. All four loose uploads matched their eight-file
ZIP, SHA-256 2ac4a1536a59907177fae64176c8b8e6ca692ad9798d07831d36b58bf9d6ae8d.
All 45 original tests passed independently. See the [adopted tool](../tools/held-expiry-assessor/README.md),
[review and changes](../tools/held-expiry-assessor/REVIEW.md) and
[original fingerprints](../tools/held-expiry-assessor/PROVENANCE.json).

Two input-validation gaps were reproduced: leading-zero provider numbers
and errno beyond the actual QNX signed-32-bit type could pass. Both are fixed.
The controller must now claim CONTROL_TRACE_OK after validating the complete
control trace before release, and watchdog cancellation follows fixture
cleanup. A proposed log marker is not proof that the action occurred; source,
compiled code and native behavior still require review.

All **50 adopted synthetic tests pass**. Stream framing and child identities
are checked, provider reply codes remain separate from reader syscall returns,
and no particular errno value is prescribed. Every example is synthetic;
none is BMW evidence. Original samples have been regenerated for the amended
proposed contract, with provenance retained.

No reader/endpoint source or binary, frozen prep/ready package, hidden stage,
firmware or HMI configuration changed. No controller or vehicle-ready trial
exists yet. Next work is implementing and testing the controller, including
bounded output/cleanup, exact child reaping and whole-trial watchdog coverage.
The log alone cannot establish authenticity or total elapsed trial time.
Actual plugin/HMI trials remain paused and live RPM is unverified.
