# ShiftDeck integration assessment and host experiment — 27 November 2026

The owner supplied Claude's [original review](evidence/2026-11-27-claude-shiftdeck-review.md),
16547 bytes, SHA-256 `53a8d962218a2a887d73409b02dbc6f43efbb203e2320cf1d20d9b4ae4c1e421`. It was read as evidence, not executed
or adopted as an instruction to change the vehicle. This assessment uses
the already-uploaded full RPM source, bridge and actual framework libraries,
as well as pinned upstream commit 8567abaadd1305965b3ad39e3222575cd49c507d.
No missing source needs to be recollected from the owner for these checks.

**Decision:** accept ShiftDeck as the narrow first reuse target. Defer
BoostDeck, native binding/lifecycle changes, assets/deployment and diagnostics.
A separate host-only receipt latch now feeds three unchanged upstream drawing
methods into a fake image-model sink. It has **24 passing synthetic tests**.
This does not establish a working native screen, native callbacks or live RPM.

## Corrections and qualifications to the supplied review

### CDS JSON is already RPM; the existing range is 0..9000

The captured native CEngineSpeed2 property publisher at 0x208558 converts its
raw u16 (except sentinel 65535) by one quarter, converts to unsigned integer,
and formats `{"RPMSpeed":%hu}`. Thus raw 3200 becomes JSON RPMSpeed 800.
Our current parser stores that JSON number directly and accepts 0..9000;
65535 is rejected. Do not divide JSON by four again or widen the current
B58 policy to the OBD/renderer 16383 ceiling.

The host test proves that a synthetic JSON value of 700 reaches image/digit
selection as 700, and that zero is distinct from unavailable. It rounds only
at the integer display boundary. Fractional test values are robustness cases,
not an observed native JSON format. The original parser/callback is unchanged.

### Receipt time is not evidence of new vehicle measurement

Our callback takes CLOCK_MONOTONIC in **seconds** and passes that receipt time
to b58::update/read. The bridge takes lifecycle_mutex and a separate telemetry
mutex; its stored reading expires when age is greater than 2.5 seconds.
It receives no producer timestamp, sequence or cache/live provenance in the
known JSON shape. The current callback's app argument is ignored rather than
dereferenced; a proposed new per-app latch must not assume the same lifetime.

Consequently it cannot identify and refuse every cached bind/async-get replay
just by inspecting the number. Repeated equal values may also be legitimate
new callbacks. The host latch explicitly records **receipt** time/sequence,
and every replay report retains producer_freshness_verified=false. UI polls
never restamp the stored time. Errors do not become zero or refresh the prior
sample. Same-value later callbacks are new receipts, not proven measurements.

The original renderer's 750 ms blanking rule is preserved solely as a pinned
host comparison baseline. It is not selected as our native CDS policy, and
the experiment does not stack a second 2.5-second bridge timeout on top.
Change-driven/periodic delivery and data provenance remain live questions.
There is no validated live signal on this car; only parser/static evidence.

### CDS removal exists; callback quiescence is still unknown

Our actual AppFramework exports
`_ZN3bmw9PluginApp36cdsRemovePropertyChangedEventHandlerERNS_11BasicStringIcEE`
at 0x587c (84 bytes). It invokes a CDS interface virtual, then looks up and
removes the property entry from the app+0x128 map when found. This establishes
an available removal path, not completion of queued/in-flight callbacks.

The subscribe, async-get and removal functions all match the donor link
inputs in size and instruction prefix. The [three-method audit](evidence/2026-11-27-cds-method-audit.json)
is additional to the earlier 50-function ShiftDeck audit; it uses our retained
donor pair as reference, not an amended upstream fingerprint. No ABI method
is added to the host wrapper and none is invoked on the car.

A stop flag only rejects updates while its latch object remains alive.
Safe native destruction/unload requires demonstrated callback lifetime and
quiescence. The prototype joins its host writer before destroying the mutex;
this is not a native unsubscribe implementation.

### Native Message dispatch/size have further static support

Sixteen instruction sites and associated function/symbol identities were
checked in the actual car's AppFramework. The [audit metadata](evidence/2026-11-27-shift-native-details-audit.json)
records the precise evidence and limits:

- PluginAppHandler::handleMessage accepts ID 1; 0x40000003 passes through.
- PluginApp::handleMessage maps 0x40000003 to the case at 0x6400, reads a
  UInt32 key, and calls vtable +0x4c (slot 19, invokeDataUpdate).
- Native enqueue at 0xa70c allocates 0x50 bytes and calls the Message copy
  constructor. The ID/Parcel constructor stores timer at +0x10 and constructs
  the embedded Parcel at +0x18. An 80-byte queue allocation therefore has
  direct support in this pair, not just in upstream's older-firmware comment.

This does not recover every type/alignment contract, prove native delivery
or establish which thread invokes either CDS or UI callbacks. The host
experiment uses neither native Message nor native PluginApp objects.

### Do not change our finalizer return type from the upstream header alone

Our full source declares void onFinalize and manually replaces vtable slots.
The actual base onFinalize at 0x5124 is 12 bytes and leaves r0 unassigned;
finalize at 0x50ec calls slot 23 then returns without testing r0. This path
provides no evidence requiring the proposed bool replacement. Mangled names
do not resolve the source return type, and the upstream declaration is not
an authoritative header. The standalone fault occurred without creating an
app object, so this mismatch is not an explanation of that captured crash.

Our PluginApp declaration is deliberately an opaque 0x200-byte storage holder
with no C++ virtual declarations, coupled to a copied/patched native vtable.
It is not the upstream reconstructed 352-byte C++ subclass base. Blindly
adding sizeof(PluginApp)==352 to the current stand-in would test the wrong
contract. Do not swap headers or compiler modes in this host experiment.
Our source posts a Runnable stand-in, not a Message declaration.

## Host-only implementation and verification

[tools/cds-shift-preview](../tools/cds-shift-preview/README.md) contains:

- A newly written C++98 pthread-mutex receipt latch with no BMW dependency.
- The complete upstream animatedRpm, digits and draw methods copied unchanged
  with original method hashes, matching constants and the MIT notice retained.
- A fake ImageID/model sink and frame input wrapper; no real screen or SDK ABI.
- A Python JSON **fixture boundary**, not a replacement production B58 parser.
- Replay checks for correct units/zero/error/range handling, timestamps,
  same-value callbacks, stale blanking, shift images, easing, visibility, stop,
  and 20,000 writes with concurrent consistent snapshots.

All **24 checks pass** with Linux g++ in C++98/no-exceptions mode. Native-facing
headers refuse __QNX__ builds. No ARM compiler/SDK, Docker, network, plugin,
manifest, image/font generation, preference write or milestone-7 edit is used.
Model IDs are tested, not actual pixels, resources or physical layout.
The pinned old source's targets are 5800/6000/6250/6500/6700; v0.7.18 headline
changes are not silently assumed. Display dimensions still need confirmation.

## Frozen Ubuntu source preparation

nbt-cds-shift-host-prep.tar.gz is 12702 bytes, SHA-256
`ad6a289516566ca3f0754837f7f27bc039616286787d8eaf04ba85554f5d783b`.
Its 13 ordinary source/checksum files were compared against the archive,
and all payload pins passed. The complete helper ran from the frozen layout:
24 tests passed in 0.272 seconds, then the synthetic demo and unique review
archive were produced. No ELF binary is shipped in this preparation.
The helper uses only Linux g++/Python; no QNX SDK or source re-patching.

## Next step and scope

Repeat the frozen host checks on Ubuntu if desired and retain their result.
Do not build/deploy a native CDS gauge from this preparation. Before native
integration, establish callback cadence/provenance, a measured display policy,
removal/lifetime/thread rules, app admission and the actual screen geometry.
Keep the earlier runtime crash investigation and eight-library collection
separate. A standalone gauge may be preferable to changing NbtAad, but its
permission and lifecycle behavior have not been established on this car.

BoostDeck's extra channels/imports, rendering assets/fonts, preferences,
installers, UDP/worker launch, HSFZ/MOST/DSI and HUD integration stay deferred.
Android Auto source and hidden candidates remain unchanged. No result here
fixes the crashes or proves native initialization, adapter-free operation or
live B58 RPM. The HMI/library-loading pause remains in force.
