# Notification trace and property-locator review — 19 November 2026

The owner supplied Claude's notification trace, a property locator, its 18
synthetic tests and an ELF metadata workaround. Originals are retained
unchanged outside this checkout. This review uses the captured original BMW
ELFs. No vehicle command or target library was executed.

## Verified trace and storage

The supplied 18 tests passed against the unmodified cache reader. Independent
disassembly confirms the provider's property map at +0x20, header at +0x24,
node value at +0x14 and lazy creation in getProperty (libhmiremoting 0x19a52c).
Thus inspection must walk existing storage instead of calling getProperty.
The RPM property and creator vtable address points are 0x6ac7c0 and 0x6a4338
relative to libhmiremoting.

Constructor calls and named vtable relocations confirm CPxyBase's members:
CFktIDs at +0x68, CNotification at +0xfc and CNotificationCheck at +0x194.
The request and final sender both check host state +0x58 against 2. The
engine-speed status decoder clears validity and sets it again only after
accepting its bounded u16 payload. Full wire semantics and vehicle delivery
remain unverified; the CNotification status decoder is not treated as proof
of successful acknowledgement merely because of its class name.

## Additional activation/retry trace

- HMI 0x20d834c is CSvcBase::setActive, corroborated by its OTF relocation.
  Activation with no delay at +0x60 writes state 2 to +0x58 and dispatches
  the activation delegate at host+0x14. With a delay it schedules a timer
  and writes pending state 1.
- Exported CSvcBase::onActivationTimer at 0x20d7398 writes state 2 at
  0x20d73f0 and dispatches that same activation delegate.
- Function initialization at 0x20dae2c registers activation through proxy
  virtual byte offset +0x24 and deactivation through +0x28. For
  CEngineSpeed2, +0x24 resolves to 0x20dbce0. If listeners exist at +0x4c,
  it sets +0x68 to literal 0x3e80 and invokes virtual +0x34 again. Timer
  units for that literal have not been established.
- CSvcProxyManager::onConfigurationStatus calls setActive(true) at
  0x20e6ef8. This does not prove the tested vehicle's particular host took
  that path.
- Captured RTTI links CPxyVehicle through primary CPxyBase to CSvcBase.
  CPxyVehicle's transmit virtual +0x18 resolves to 0x20d75ec, forwarding
  through the sink at host+0x30 and that sink's virtual +8. The concrete
  live sink and route remain to be verified.

This explains how a deferred notification request can be retried after
activation. Live state, successful sends and RPM delivery remain unverified.

## Locator corrections

The reviewed [module](../tools/native-cache-reader/rpm_property_locator.py)
only reads existing memory. It calls no target API and creates, binds and
modifies no native object.

- Missing entry means absent in this provider snapshot. Clear flags do not
  prove "never bound": unbind clears +0x69 and unsubscribe clears +0x68.
- State 2 passes one early gate; it does not prove a send occurred.
- COW strings are read by exact length, avoiding the original 48-byte
  prefetch beyond a short allocation.
- Provider/environment/vehicle/proxy and property/creator types are checked.
  Property environment or proxy mismatch stops inspection.
- Every visited region is recorded and rechecked, including tree nodes,
  key bytes, list nodes and host state. The original final check omitted
  the host state and some node data. Rechecks are best-effort, not an
  atomic snapshot or validation of the entire tree.
- Tree parent/order/cycle and handler-pointer guards were added. Results
  are stored per provider. The explicit `--inspect-property` flag requires
  `--read-cache`; mappings-only requests no process-memory reads.
- Request-state field labels were corrected: host+0x34 is the u16 device
  address, +0x36 the FBlock ID and +0x37 the instance ID. This is supported
  by the native SvcBase diagnostic and header assembly at 0x20db64c; these
  fields must not be confused with UDS ECU addresses.

All 53 offline tests pass: 27 cache-reader/CLI tests and 26 locator tests.
Added cases cover changes inside tree/list nodes with stable headers, host
state changes, a key ending at a mapping boundary, identity mismatch and the
mode requirement. The supplied map fixture's parent/extrema links were
corrected. The new property-inspection mode has not run on the vehicle.

## ELF workaround verification

The missing reports were independently regenerated from fixelf.py in an
isolated directory. Disk readback and full byte comparison confirmed exactly
two changed bytes per copy, with all original inputs unchanged:

| Original | Field offset | Old index | New index |
| --- | --- | ---: | --- |
| HmiMain3D-car | 0x1f24a | 34 | SHN_ABS / 0xfff1 |
| libhmiplugin.so | 0x5fce | 33 | SHN_ABS / 0xfff1 |
| libhmiremoting.so | 0x3fe4e | 35 | SHN_ABS / 0xfff1 |

The supplied script checks its in-memory output but does not actually
re-read the written file; this review performed that check independently.
Its rule applies generically to invalid symbol indexes, so this is not an
endorsement of marking arbitrary symbols absolute. No LLVM disassembler was
available here; metadata and file integrity were checked independently.
Reports and modified binary copies remain outside GitHub. Modified copies
are analysis-only and never replace deployment originals. We do not need
Claude's original reports to continue.

## Next observation

A future planned connection can inspect an existing property's current
flags/list and function-block state with a fresh PID and all existing
fingerprint/type/read-budget guards. No activation is part of this mode.
Do not reconnect solely for this offline review. Live B58 RPM is still
unverified; library-load/unload probes and HMI activation remain paused.
