# Initial RPM async-get source preparation — 20 November 2026

The owner resumed on Ubuntu. The prior [native trace](2026-11-20-cds-async-get-review.md)
and the owner's pasted Claude review agree that the normal RPM bind path
registers notifications, while async-get adds a distinct query. The Claude
response is independent supporting analysis, not evidence of live data or
an instruction to activate the plugin.

## Prepared change

Patch 5 changes only rhmiapp/nbt_aad_app.cpp:

- Declare the existing non-virtual PluginApp::cdsGetPropertyAsync method.
- In the existing delayed initialization runnable, call it for RPM after
  cdsAddPropertyChangedEventHandler, using the same property/delegate pair.
- Retain the existing b58.disable condition. Add no polling or timers.
- Log before the get call and after it returns. Rename the old RPM
  subscription log so it reports a returned call rather than claiming that
  registration succeeded.

There is one explicit get per execution of the existing initialization
runnable. This is not a new process-wide once-only guard. Other telemetry
subscriptions and Android Auto implementation are not edited.

The actual car and existing link-time AppFramework both export exactly:

`_ZN3bmw9PluginApp19cdsGetPropertyAsyncERNS_11BasicStringIcEERKNS_8DelegateIbRKNS1_ItEEvvvEE`

The reviewed declaration uses the existing CdsDelegate alias. Both wrappers
copy its two words into the same property-keyed callback map. Reusing the
same object/callback pair avoids replacing the RPM handler with a different
callback. The wrappers do not retain pointers to the stack-local delegate
pair itself. This is not a complete proof of host scheduling or app lifetime;
the original initialization/finalization behavior has not been redesigned.

## Exact source revisions

Before (uploaded 17 November stream-cleanup source):

`1fa48b7a903cfb7aeb2d59abb703b3bdafe291bbc8ebc7c28a109eeb262510be`

After (prepared source only):

`1b3b8e343dcabea75036e2c473ccc71a51a2cbd240c84d5de5eb070e0accf853`

Patch 5 SHA-256:

`404e67c44feaf3cabd32fe10089f08a72dd54339fd2c565ae0f92036812274ae`

The helper tools/prepare_initial_rpm_get.py defaults to checking this exact
baseline without editing. With --apply it creates an exclusive backup named
nbt_aad_app.cpp.before-20261120-initial-get, checks the source again before
writing, and verifies the output hash. It refuses a linked/missing source,
revision mismatch or existing backup; an already matching prepared source
is left alone. Use the helper or patch, not both.

## Validation and next Ubuntu step

On a separate matching source copy, git apply --check passed. Helper check
mode left the file unchanged. Helper application and git apply produced
identical reviewed output, and the preserved backup matched the original.
The new method's exact export exists in both reviewed framework libraries.

No QNX build was run here; the owner's Docker image is on their Ubuntu VM.
No updated libNbtAad.so has been reviewed. The existing reviewed binary
remains the 17 November candidate; its fingerprint is not superseded by
the new source hash. A returned call log would not prove a successful bind,
transmission, ECU reply, fresh RPM, or instrument-cluster agreement.

First verify the owner's current Ubuntu source hash. If it matches, prepare
the source and rebuild the RHMI target there for offline import/relocation
review. Keep platform libraries and the working Android Auto source intact.
The separate app-admission/initialization investigation remains outstanding;
adding async-get does not resolve the earlier missing plugin mapping or
standalone framework shutdown fault. Vehicle execution remains paused.
