# FreZZZeR projects and linked iDriveDeck review — 27 November 2026

The owner supplied FreZZZeR/nbtevo-diag and FreZZZeR/nbtevo-id6-apps.
Both were cloned and inspected at pinned commits. Their migration notice led
to the linked ID6 Apps fork and current upstream, now branded **iDriveDeck**.
Only source, package bytes and Linux host tests were inspected. Nothing was
installed or executed on the BMW; no release/installer script was run.

## What already exists

| Repository / snapshot | What the checked source establishes |
| --- | --- |
| [nbtevo-diag](https://github.com/FreZZZeR/nbtevo-diag/tree/e550bdadebe9cb060ecab1630893ebed433ec4c2) | Python ENET/HSFZ diagnostic/catalog/probing/deployment tooling, focused on an F30 N57; not a completed native gauge application |
| [nbtevo-id6-apps](https://github.com/FreZZZeR/nbtevo-id6-apps/tree/e4fb4ce2ab51e7c48f7cab9b805a963dd5918672) | Native prototype with workers, frames, presentation and ABI header; development is migrating to ID6 Apps |
| [FreZZZeR migration fork](https://github.com/FreZZZeR/ID6_apps_prerelease/tree/9113c26ef08999b5eab8bcd5f13227b3225bcaae) | ID6 Apps v0.7.4 snapshot with released native app packages |
| [Current upstream / iDriveDeck](https://github.com/inotbarnacle/ID6_apps_prerelease/tree/8567abaadd1305965b3ad39e3222575cd49c507d) | Release documentation v0.7.18, native BoostDeck/ShiftDeck source and packaged executables, gauges/RPM display, supported framework profiles and reported vehicle results |

Similar native gauges have therefore already been built in the linked
upstream. That does not mean the two originally requested prototypes are a
finished solution or that our exact adapter-free B58 requirement is proven.

## Why the requested native prototype is not install-ready

Concrete source checks, rather than headline claims:

- [collector_main.c lines 42–58](https://github.com/FreZZZeR/nbtevo-id6-apps/blob/e4fb4ce2ab51e7c48f7cab9b805a963dd5918672/native/src/collector_main.c#L42): real HSFZ framing/connection is TODO; hsfz_send always returns -1 and gw is null. No live ECU data can arrive through that implementation.
- [plugin.cpp lines 68–98](https://github.com/FreZZZeR/nbtevo-id6-apps/blob/e4fb4ce2ab51e7c48f7cab9b805a963dd5918672/native/src/plugin.cpp#L68): worker launch and periodic poll scheduling are TODO. Calling poll once does not implement a live gauge loop.
- [plugin.cpp lines 121–138](https://github.com/FreZZZeR/nbtevo-id6-apps/blob/e4fb4ce2ab51e7c48f7cab9b805a963dd5918672/native/src/plugin.cpp#L121): exports nbtevo_diag_plugin with an incomplete descriptor, while our captured HMI explicitly looks up pluginAppInfo with create/destroy at +0x10/+0x14. This source would need correction before use with that loader.
- The XML is a text-label sensor layout, not evidence of functioning circular gauges on the vehicle. DIDs and factory N57 scaling are not evidence for this B58 DME.

The Python README's broad read-only language must be read alongside its code:
DTC clearing and drivetrain actuation paths exist, and dynamic-DID reads clear/
define F303 with service 2C. None of these paths was exercised against a car
in this review. No vehicle command from those repositories is recommended here.

## Direct relevance of the released upstream

The [upstream compatibility records](https://github.com/inotbarnacle/ID6_apps_prerelease/blob/8567abaadd1305965b3ad39e3222575cd49c507d/source/docs/COMPATIBILITY.md)
and installer-profiles.json contain our exact **vehicle** framework pair:

| File | Our actual car SHA-256 |
| --- | --- |
| AppFramework | 057618b81375564f5255308a3c59111dd1e9eb57e43e38b7a858bff04ab41ce5 |
| CoreFramework | 7c6ad2a7134adf8385435487301c88a192a0e8e3bf1bf5ae5c858eb4f92d8202 |

It matches Q18491I, R19101I, R19144I and T18501I entries. This does not identify
our actual firmware label. The donor libraries used by our Ubuntu build are
a different pair, corresponding to the upstream Y21432J/T21424I group.

Codex read the upstream dashboard.zip at that exact commit (681018 bytes,
SHA-256 36ec7fce93c73b62342290e91429c89d68a64e8aed97fb62b5a4dd50be66d023)
and extracted only the two ShiftDeck artifacts for file inspection:

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| libShiftDeck.so | 49048 | 5b7cd9c61eafcef43767dc509aee1d1239eed0fb748e6ed05b5980733cf31313 |
| shift-deck-qnx | 42759 | dab4c1644ac72221464dd18fc255cbc547b3934808f48b9845f54a7493328787 |

The unmodified upstream audit_framework_abi.py was run with its public
fingerprint, that packaged plugin and our actual captured framework pair.
It passed **50 function size/instruction-prefix comparisons and the vtable
checks**, with no failures. See the [full metadata report](evidence/2026-11-27-shiftdeck-framework-audit.json).
This is static evidence, not a fix for our old crash or a native load test.
The upstream compatibility notes report freezes on some R19144I units sharing
this pair as well as successes on other units. Exact hashes are necessary
context, not a guarantee of runtime stability.

The packaged plugin exports the expected 24-byte pluginAppInfo and has no
mandatory ios_base initialization imports. It links AppFramework/CoreFramework,
GNU libstdc++, libc, libm and libsocket. The worker is a separate C ARM/QNX
executable whose direct dependencies are libc, libm and libsocket. Its strings
include the MOST transport and DSI library/server names, consistent with the
source; that presence alone does not validate its native behavior.

## RPM route and the no-adapter limit

[ShiftDeck's worker](https://github.com/inotbarnacle/ID6_apps_prerelease/blob/8567abaadd1305965b3ad39e3222575cd49c507d/source/native/src/workers/shift_deck_worker.c)
reads DME 0x12 using OBD 01 0C; two returned bytes decode as big-endian raw/4.
It sends samples to a native HMI plugin over local UDP. It does not obtain
RPM by subscribing to CDS engine.RPMSpeed. Its genuine HSFZ implementation,
worker lifecycle and interface code are useful references for us.

The [MOST fallback implementation and status](https://github.com/inotbarnacle/ID6_apps_prerelease/blob/8567abaadd1305965b3ad39e3222575cd49c507d/source/docs/MOST.md)
are especially relevant: diagnostic requests can use DSYSMOSTServer rather
than depend on external ENET gateway reachability. The source uses FBlock
0x06, instance 0xF0, FktID 0x050 and routine 0x0F0B with source 0x63.
It reaches only DME 0x12; EGS transmission temperature is not covered.

Limits stated by upstream must not be lost:

- Their own N20 custom port reportedly performed DME service 22 reads with
  nothing connected to OBD; this is an upstream report, not a Codex/B58 result.
- The shared port is documented as not yet run on a car, and **OBD service 01
  is explicitly untested over MOST**. Thus implemented RPM polling plus MOST
  support does not prove adapter-free RPM on our M140i.
- Simulator DSI setup reaches no physical target. Fake DSI tests cannot
  establish vehicle delivery or scaling.
- The native-Android-Auto coexistence guard forces HSFZ if NbtAad is detected.
  Preserving future Android Auto requires reviewing that behavior separately.
- The DSI binder dynamically loads libsys_dsi_base.cpp-ne.so.4 and uses its
  reconstructed ABI. Our library-loading/runtime pause is not bypassed by
  the collector being C or by an upstream simulator success.

A separate [M140i report referenced by upstream](https://github.com/inotbarnacle/ID6_apps_prerelease/issues/108)
describes an ENET-unplugged routing/ARP problem for transmission readings.
That reinforces keeping native UI compatibility, ECU response support and
adapter-free transport as distinct questions.

## Checks actually run

- nbtevo-diag: **28 Python tests passed**, 0.06 s, pytest 9.2.0 and evocode
  0.5.0 in a private review venv. Canned gateway and fake deployment only.
- nbtevo-id6-apps: default make test passes the first six C test programs,
  then stops compiling the final collector test because current host GCC
  treats its misleading indentation warning as an error. The same final
  test passes when only -Wno-error=misleading-indentation is added; no source
  was changed. Both plugin C++ and collector C syntax checks pass. This is
  not an unqualified pass of the original make test command.
- Linked upstream: focused core test passed; **130 MOST checks and 25 diag-link
  cases passed**, zero failures, against fake DSI/DME. These are selected
  host tests, not its full suite and not QNX execution.
- Packaged ShiftDeck static framework audit: 50 function prefixes plus
  vtables passed as above. No installer, ARM library or worker was executed.

All frozen revisions and package identities are in the
[review metadata](evidence/2026-11-27-frezzzer-review.json).
The requested projects are Apache-2.0, with an attributed MIT ABI header.
The linked upstream native source is MIT. Any adopted code must retain its
applicable notices; no external application code is integrated in this commit.

## Effect on our plan

Use upstream ShiftDeck/BoostDeck as a candidate base/reference for gauge UI
and native plugin/worker integration. That can save custom implementation
work. Before any change on the car, assess exact package/firmware/display,
normal initialization and recovery, then prove the RPM transport on this B58
with the adapter absent. Keep UI adoption and CDS-versus-diagnostics choice
separate. No tuner, drivetrain, coding, firmware or restart action is included.

The eight-library read-only collection remains useful for investigating the
old mixed-runtime fault. It is not a reason to ignore this existing native
implementation, nor does the new implementation establish that the fault
is fixed. Preserve milestone-7 and both hidden candidates. Actual plugin/HMI
loading remains paused; live RPM on our car is unverified.
