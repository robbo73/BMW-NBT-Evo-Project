# CDS bind investigation and handover — 19 November 2026

This reviews an external static-analysis handover supplied by the owner.
Findings below were independently checked against the captured vehicle ELFs,
without running a vehicle program or modifying the original files. The
[vehicle checkpoint](2026-11-19-native-cache-checkpoint.md) remains the
runtime baseline: both engine-off and about-700-RPM idle observations reached
the expected proxy but returned invalid status, raw zero and null RPM.

## Confirmed activation path

- `TPC<CCdsPropertyEngineRPMSpeed>::createProperty`, libhmiremoting ELF VA
  0x1efa40, links the property to Vehicle+0x4508 through property+0x64 and
  initializes property flags +0x68 and +0x69 to zero. These are fields of
  the property object, not the engine-speed proxy.
- `CCarDataProperty::bind` at 0x1a1c4c adds a handler to its list. The prior
  first node is compared with the list sentinel; only the previously empty
  case invokes property-vtable byte offset 0x10. The RPM vtable resolves
  that slot to `_TSimpleProperty<CPxyVehicle::CEngineSpeed2>::_bind` at
  0x1ec3cc. The subsequent slot 0x14 is `_bindResponse` at 0x1a18dc.
- `_bind` connects through proxy+0x4c using the routine at 0x308e28 and sets
  property+0x69. A callback connection is distinct from delivery of a valid
  engine-speed message; the flag alone does not prove reception.
- The connection routine's first-listener path calls its owner's vtable
  byte offset 0x34. The owner is the engine-speed proxy. Its HMI address
  point is 0x038e2bd0, so that virtual entry resolves to 0x020dc374.
- At 0x020dc374 the code checks proxy+0x10 for its associated function block,
  tests function-block+0x58 against 2, serializes the u16 function identifier
  at proxy+0x18, performs a CPxyBase cast, handles notification timing and
  eventually calls 0x020caadc with the CPxyBase subobject at +0xfc. The
  exact wire/service meaning and routing of that downstream call still
  need to be established. Do not infer successful transmission simply
  because the connect/bind path was entered.
- The earlier identified status handler at HMI 0x023aa92c decodes the raw
  value at proxy+0x78 and updates validity through 0x020dc560 before notifying
  callback lists. The native CDS property applies raw/4 to valid data.

## Error branches, independently decoded

`CCarDataMainProvider::availabilityOfProperty` is at libhmiremoting ELF VA
0x19cb84. `handleBindProperty` at 0x19cfa0 checks its result before calling
`CCarDataProperty::bind`, or reports an error through the handler.

| Decimal value | Branch condition in this implementation |
| --- | --- |
| 400 / 0x190 | `getProperty` returned null; lookup/creation did not yield a property. |
| 401 / 0x191 | Property enabled byte at +0x14 is zero. |
| 402 / 0x192 | Required permission bit is missing, **or** the property's virtual coded/availability check returned false. |

A nonzero result from the authentication/permission handler can also be
propagated. These are observed CDS implementation branches, not an assertion
that the numbers carry standard HTTP meanings or official enum names.
`errorStringForError` at 0x19ce98 formats `{"error":%d}`;
`reportError` at 0x19cf34 forwards that payload through the handler callback.

The RPM coded predicate checks the associated function-block pointer at
proxy+0x10. The reader observed that pointer as nonzero. This supports that
one predicate for the observed proxy, but does not establish the property
enabled flag, permissions, an attempted bind, or notification delivery.
There has been no observed runtime bind error, so permissions cannot yet be
ranked as the likely failure from these checks alone.

## Limits of the proposed diagnosis

The static lifecycle makes a missing consumer/subscription a reasonable
hypothesis for an inactive cache. It does not establish that this was the
runtime cause. The current reader did not inspect a live RPM property
instance, its handler list, or its +0x68/+0x69 state flags.

Absence of the literal `engine.RPMSpeed` from HmiMain3D or libhmiplugin does
not prove absence of all consumers or proxy users. Clients can bind by a
numeric ID, access the native proxy directly, use external resource data or
live in another library/process. Conversely, finding the literal does not
prove that a bind executed in the tested session.

The SSH/dd inspection path has been exercised successfully. The vehicle-to-
HMI status/notification transport has **not** been verified and remains a
separate question. An invalid cache can be consistent with absent demand,
inactive service state, failed notification setup or absent incoming data.

The source's `B58 CDS handler registered` log follows a void framework API
call; it is not evidence of a successful remote bind. The current callback
logs received ASCII payloads before parsing, so an error JSON would be
visible if delivered to that callback. Complete error propagation through
the connector/app dispatcher has not been demonstrated on the vehicle.

## Focused follow-up to share with Claude

1. Continue from engine-speed proxy virtual +0x34 = HMI 0x020dc374. Decode
   the downstream call at 0x020caadc and onward: function-block/service IDs,
   message operation and notification setup, routing, replies and state-2
   gating. Identify source instructions/constants and separate verified
   protocol meaning from interpretation. Do not execute requests on the car.
2. Derive a read-only path from an existing CCarDataMainProvider to an
   **already-created** RPM property instance, if present. Document cache
   layout, type checks and handler-list/flag reads so that the unbound
   hypothesis can be tested. Do not call getProperty/createProperty/bind or
   infer that an object exists because its factory is registered.
3. Check possible direct/native proxy users or numeric-ID consumers before
   asserting that no stock consumer exists. Restrict absence claims to the
   exact files and searches performed.
4. Share `fixelf.py`, the tool/version/error it addresses, original hashes,
   and the exact metadata changes and output hashes. Keep untouched originals
   as the evidence and deployment baseline.

## ELF tooling cross-check

The unmodified HMI, libhmiremoting and libhmiplugin each contain an out-of-
range concrete section index on the dynamic `_stack` symbol (34, 35 and 33
respectively; the files have 27, 28 and 26 section headers). libhmicom shows
the same class of issue. This corroborates the metadata observation, but no
particular repair script has been reviewed. Our pyelftools/Capstone readers
use the original image bytes and addresses without modifying these files.
A metadata workaround is not a runtime fix and must not be substituted for
the originals in build/deployment or checkpoint comparisons.

Fourteen exact ARM instruction checks plus the native proxy virtual target
were asserted offline for this review. No plugin changes, vehicle memory
writes, library loading, HMI activation or coding changes were performed.
The existing pause on vehicle library-load/unload experiments remains.

The [notification/locator review](2026-11-19-notification-locator-review.md)
checks the supplied follow-up, corrects historical-state inferences, traces
activation/retry and prepares opt-in read-only property inspection. That
new vehicle mode remains untested on the car.
