# Native RPM cache inspection — 19 November 2026

## Confirmed vehicle observations

The owner ran the client reader from Chromebook Linux against the existing
HmiMain3D process on hu-omap. The current PID was 278582. After removing the
nested remote grep expression, mappings-only mode completed with zero
process-memory reads. The observed module bases were:

| Module | Base |
| --- | --- |
| libstdc++.so.6 | 0x7899f000 |
| libhmiplugin.so | 0x78f9b000 |
| libhmiremoting.so | 0x79800000 |

These addresses and PID are historical observations, not reusable constants.
The report's `hmi: 0x0` is the reader's convention for the inspected HMI's
fixed ET_EXEC addresses; it is not a claim that HMI loads at address zero.

Two subsequent cache-mode runs completed. Each passed four small code/header
fingerprints and the expected vtable/pointer checks and read 1012 bytes in
69 bounded calls. This validates the exercised inspection path, not the
entire binary ABI or a live telemetry feed. No plugin or target executable
was installed or run, no diagnostic request was sent and no target memory
was written by the reader.

| Vehicle state, reported by owner | Samples | Raw u16 | Status valid | +0x10 nonzero | Interpreted RPM |
| --- | ---: | ---: | --- | --- | --- |
| Engine off | 3 | 0 in all | false in all | true in all | null in all |
| Engine running, cluster about 700 RPM | 3 | 0 in all | false in all | true in all | null in all |

Both runs reached the same existing objects:

- Scope: 0x03a96a68
- Provider: 0x0a373398
- Engine-speed proxy: 0x0a5ec520

Report filenames on the Chromebook were `nbt-cache-samples-1.json` and
`nbt-cache-engine-idle-1.json`. These observations come from the owner's
pasted reports and engine-state clarification; the cloud workspace did not
connect to the vehicle. The full JSON files remain on the Chromebook.

The invalid status means raw zero must not be treated as zero engine RPM.
The engine-off state does not fully explain the result, because the cache
remained invalid during the idle test. Neither successful CDS callback
delivery nor fresh/changing RPM nor cluster agreement has been established.

## Additional offline code findings

The field reported by the historical reader key
`registration_word_nonzero` has a narrower meaning than an active
subscription. In the captured HMI, the validity routine at 0x20dc560 reads
+0x10 at instruction 0x20dc57c and asserts `m_pFBlock != nullptr` if null.
This identifies the field as the associated function-block pointer.
The RPM wrapper's `_isCoded()` at libhmiremoting ELF VA 0x1cb714 tests that
field for nonzero. It is not a subscriber count, and true does not establish
that RPM notification is active or that a response has arrived.

The RPM cached-value getter at libhmiremoting 0x4ccb7c tests valid byte +0x60
and copies u16 +0x78 only when valid. Its invalid branch reaches the common
error/status reporting routine at 0x3146dc; reading this cache does not itself
activate or refresh it. The observer never calls that getter.

Subscription/binding is separate:

- `_TSimpleProperty<CPxyVehicle::CEngineSpeed2>::subscribeStatus()` at
  0x1e4064 attaches a callback to proxy+0x6c and maintains its own flags.
- `_bind()` at 0x1ec3cc connects through proxy+0x4c. The common connection
  routine at 0x308e28 has a separate first-listener/notification path.
- In HMI, CEngineSpeed2's status-message handler at 0x23aa92c handles a
  status message, decodes the u16 into +0x78, sets valid via the routine at
  0x20dc560, then notifies the callback lists at +0x4c and +0x6c.

Those static paths support investigating signal activation and notification
routing next. They do not prove that a subscription is absent in the tested
session, that a particular stock screen activates it, or that a subscription
alone would make RPM arrive on this firmware.

## Next work

Trace the stock CDS property's creation, bind and request lifecycle and the
engine-speed notification route offline. Establish a supported activation
path before proposing a further vehicle test. Merely repeating passive reads
or changing RPM scaling does not resolve the observed invalid status.

Library-load/unload probes and plugin/HMI activation remain paused following
the earlier exit faults and head-unit restarts. Do not change memory flags,
force the valid byte, replace runtimes or inject calls into the running HMI.
No further vehicle commands are needed for the current offline follow-up.
