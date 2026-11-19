# Sports Displays requests and notifications — 20 November 2026

Follow-up to the [initial display trace](2026-11-20-sports-displays-review.md),
using the same unchanged captured HmiMain3D. The question was whether the
display makes a diagnostic call before receiving data. Static analysis
finds a native notification subscription and a separate state-related
event publication. It does not establish an HSFZ/UDS request in this path.

## Subscription for gauge values

CPxyVehicle's constructor at 0x23c503c identifies the previously located
embedded proxies by their relocated vtables:

| Vehicle offset | Concrete proxy | Status decoder |
| --- | --- | --- |
| +0x369c | CVehicleDynamicEngineScaling | 0x23cb064 |
| +0x3728 | CVehicleDynamicEngine | 0x23ab870 |

The reviewed vtable stores are at 0x23c6fa8 (scaling) and 0x23c7000
(gauge values). Their object offsets are computed across several
instructions and were checked with the complete sequence.

CDevCarInstrumentsOfSport::init at 0xee56d8 registers callbacks on these
proxies' +0x4c delegate lists via 0x20dbfcc (calls at 0xee57a4 and
0xee57d0). The registration helper checks the prior listener count. On
the first-listener path it invokes the proxy's virtual +0x34 method.
Both reviewed proxy vtables select the common method at 0x20dc374.

That method checks its function-block host state at +0x58. When state is
2, it serializes the proxy function ID and calls CPxyBase::CNotification
at host+0xfc, via 0x20caadc. The latter explicitly logs
`Trying to set/clr notification(s): Ctrl=%d, DevID=%04X, FktIDs=` and builds
a native service message. The reviewed call supplies notification control
1 and the current service-manager device ID. The proxy send path also
checks function-block readiness before forwarding to the host's transport
virtual method. A non-ready state defers the request; registration alone
does not prove transmission.

When values arrive, CVehicleDynamicEngine's decoder at 0x23ab870 accepts
operation type 0x0c, clears validity, decodes two bounded byte fields into
proxy+0x78/+0x79, then marks the proxy valid and notifies its delegates.
The scaling proxy has a separate decoder and payload. The message numbers
are native service identifiers; they are not UDS service/DID values.

## Separate display-state event

The activity helper at 0x9924a0 derives a boolean from activity+0xd8 and
an additional variant/clamp condition. When that effective state changes,
it invokes IDevCarInstrumentsOfSport's virtual +0x20 method. The concrete
secondary-vtable adjustment thunk reaches 0xee55e0.

That device method stops an existing timer. For true it starts the timer;
for false it immediately calls 0xee53c8(false). The timer callback at
0xee5420 calls 0xee53c8(true). Initialization configures the timer with
0xc8 and 0; this review does not infer a required response deadline from
those parameters.

At 0xee53c8 the device uses its CStbManMachineInterface pointer (+0x44):

1. It sets the embedded function's value to zero.
2. It then sets it to 0x16 for true, or 0x17 for false.
3. It publishes the resulting value using 0x2418abc, with arguments
   1 and 0xffff.

The embedded function is at stub+0x470. Its constructor at 0x241d018
explicitly installs the **CActionSpecialFunctionButtonMFL** vtable at
0x241d180. The name is established by the symbol relocation; it is not a
guessed label based on the screen's purpose.

The setter at 0x24198a4 marks a changed value and stores a u16 at +0x28.
The publisher builds an operation-0x0c status containing that u16 and
passes it to CSvcFunctionStub::status at 0x20dcf58. With the observed mode
argument 1, that routine sends to its registered recipient list through
the function-block host's virtual +0x18 method, then clears the change
flag. If no relevant recipients are registered, this path does not prove
an event reaches an ECU. The zero setter is not a second publication in
this helper.

Thus there is an explicit state-related native event in addition to the
data subscription. The 0x16/0x17 branch selection is proven statically;
their meaning at the recipient and whether this event enables the gauge
feed are not yet proven. It is not appropriate to replay these values as
a diagnostic command or to describe them as a verified DME handshake.

## What remains unknown

- Which live recipients subscribe to the state event and how they handle it.
- Whether the event is required for power/torque publication, and whether
  the native service gateway translates it into another bus operation.
- The complete physical wire route and any downstream ECU diagnostics.
- Whether an equivalent activation is needed for engine-speed delivery.
  CEngineSpeed2 shares the general notification machinery, but it is a
  different function from the normalized Sports Displays inputs.
- Whether any relevant requests/responses occurred in the owner's car.
  No live trace or new vehicle execution was performed for this review.

The next offline step is the state event's recipient/routing path. A
later bounded observation with the stock screen closed/open may help,
but no target injection, event replay, coding edit or plugin activation
is proposed here. The prior load/unload probe pause remains in effect.

This checkpoint adds documentation only. No BMW binaries, raw firmware
payloads or live coding data are committed.
