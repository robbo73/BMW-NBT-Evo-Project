# Native CDS subscription versus async-get — 20 November 2026

The owner supplied a third-party suggestion that a CDS client should
subscribe and then call getPropertyAsync. This review independently traces
the native RHMI PluginApp route in the captured vehicle libraries. It does
not treat a phone-side API sequence as a specification for this native API.
No source change, rebuild or vehicle execution was performed.

## Finding

The native app subscription and async-get methods take distinct paths.
The normal initial subscription path reviewed here binds a handler and
requests notifications on the first-listener path. It does not call the
separate RPM async-get method. A bind response can return already stored
property JSON, so an initial callback does not inherently require a new get.

For RPM, the separate async-get path queues a request handler and dispatches
an explicit native service query. This is a concrete candidate for later
controlled validation, not proof that it is mandatory, sufficient, or the
cause of the earlier invalid cache and missing plugin mapping.

## App-facing paths

Actual libAppFramework.A.so exports:

- PluginApp::cdsAddPropertyChangedEventHandler at 0x7f8c: property name,
  unsigned argument, and Delegate<bool, BasicString<unsigned short> const&>.
- PluginApp::cdsGetPropertyAsync at 0x7fd8: property name and the same
  delegate type; no Connected-app numeric property identifier is passed.

The subscription wrapper copies the two delegate words into the app's
property-keyed handler map at app+0x128, then calls connector virtual +0x9c.
The get wrapper calls connector virtual +0x94 and then stores the delegate
in that same map. The order and shared storage matter for future callback
lifetime/threading review; this audit is not a runtime ordering guarantee.

The local connector constructor at HMI 0x243eb74 creates a
CLocalCommAdapter at connector+4. Its constructor at 0x2443584 installs the
reviewed concrete adapter vtable. Resolving these tables gives:

| Stage | Subscription | Async-get |
| --- | --- | --- |
| CLocalPluginAppConnector | 0x243dd30, adapter virtual +0x4c | 0x243dce0, adapter virtual +0x44 |
| CLocalCommAdapter | 0x2440acc | 0x2440b44 |
| Existing ICarDataServer interface | virtual +0x14 | virtual +0x0c |
| CCarDataMainProvider | bindProperty, 0x19ae40 | getPropertyValue, 0x19b6f4 |

The adapter obtains ICarDataServer through the existing plugin registry
helper at 0x244512c. It passes its event-handler subobject (+0x104), the
requested property string and session/context data. No cds_create call or
phone handle is inserted into this native route.

## Subscription detail

bindProperty marshals _bindProperty (0x19a7a8), which calls
CCarDataProvider2::bindPropertyChangedEvent at 0x19819c. On its first
property-handler path this reaches provider virtual +0x44, resolved to
handleBindProperty (0x19cfa0), then CCarDataProperty::bind (0x1a1c4c).

Property bind adds its handler. If the persistent list was previously
empty it invokes property virtual +0x10: the RPM _bind at 0x1ec3cc. That
attaches to proxy+0x4c. The underlying first-listener path invokes the
native Notification machinery already traced in the notification review.
It does not call the RPM explicit-get helper at 0x4c3350 on this normal path.

Bind then invokes _bindResponse at 0x1a18dc. This checks the property's
stored JSON length and forwards it to the handler only when nonempty.
That is existing property data, with freshness not established by this
operation. Notification retries and upstream routing are separate issues;
this does not claim that no other consumer or timeout can ever issue a get.

## Async-get detail

getPropertyValue marshals _getPropertyValue (0x19a860), which calls
CCarDataProvider2::getPropertyValueAsync (0x19882c). Its new-pending-property
path reaches provider virtual +0x3c, resolved to getValueAsyncProperty
(0x19d16c). Availability/authorization checks precede lookup and dispatch.
Existing pending requests can share an in-flight operation; each API call
is not a guarantee of a separate physical request.

CCarDataProperty::getValueAsync (0x1a1aa4) queues a handler and invokes
property virtual +0x20. The actual RPM vtable resolves this to
TSimpleProperty<CEngineSpeed2>::_getAsync at 0x1f1eec:

1. Call the base _getAsync at 0x1cb770, which invokes virtual +0x40.
   This resolves to subscribeStatus at 0x1e4064. That adds a temporary
   proxy+0x6c listener only when neither the bound nor subscribed flag is
   already set; a persistent bind can already provide the listener.
2. If the property is enabled, use its proxy pointer (+0x64) and call
   0x4c3350.
3. That helper builds a native message through 0x3084a8 with operation
   value 1, then invokes 0x308834 to send it.
4. The sender forwards through the function-block host's virtual +0x18
   only when host state +0x58 is 2. Missing/inactive hosts have failure
   paths; successful ECU delivery and a fresh reply remain unverified.

This is distinct from the plain cache-value getter at 0x4ccb7c. The
operation value belongs to this native service protocol, not to UDS.

## Validation, limits and independent-review questions

An offline audit checked 19 key ARM instructions and three relocated RPM
vtable targets against the original captured ELFs. Source identities remain
the previously recorded HMI, AppFramework and libhmiremoting SHA-256 values.
Annotated disassemblies and the audit JSON are retained outside Git; no BMW
binaries are committed. These are static checks, not vehicle test results.

The reviewed source registers the RPM handler but has no explicit async-get
call. The candidate has not been demonstrated running in HMI. Adding a get
cannot fix app admission, library loading, initialization or permission
failures that prevent reaching either API.

Useful questions for an independent review, including Claude if desired:

- Verify the resolved connector/adapter/provider virtual slots and the
  normal bind versus explicit-get distinction in these exact firmware files.
- Check whether any untraced scheduling, callback or retry behavior changes
  the interpretation of initial delivery.
- Review shared per-property callback storage and the get wrapper's order
  before proposing any source patch.
- Assess a future native subscribe-plus-get experiment only after the
  existing initialization/runtime failure and recovery procedure are resolved.

No plugin activation, standalone load/unload probe, native event replay or
coding change is authorized by this finding. Live engine-speed publication,
freshness, cluster agreement and the final dashboard remain unverified.
