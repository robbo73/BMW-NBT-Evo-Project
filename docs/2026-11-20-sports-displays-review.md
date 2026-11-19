# Sports Displays: initial offline trace — 20 November 2026

The owner suggested inspecting the built-in power/torque display as another
route toward native B58 telemetry. Previous checkpoints had not traced this
screen's data path. This initial review uses the already captured, unchanged
HmiMain3D and libhmiremoting.so; no new vehicle session or target execution
was needed.

## Findings from the captured firmware

HmiMain3D contains CCarInstrumentsOfSportActivity and its
`current_value_power` / `current_value_torque` graphic-model fields.

- Activity initialization at 0x9934f0 requests the existing interface named
  `IDevCarInstrumentsOfSport`. The scope-cache pointer is stored at activity
  +0xb8. The device implementation is CDevCarInstrumentsOfSport.
- The activity's update routine at 0x993d28 reads separate virtual getters
  at interface slots +0x14 and +0x18. It skips the corresponding update when
  the getter returns 255, otherwise converts the integer to float and
  multiplies by approximately 0.01 before writing the graphic-model field.
  This routine does not derive power from RPM, torque or road speed.
- The concrete interface uses a secondary vtable with offset-to-top -0x18.
  Its +0x14/+0x18 entries are adjustment thunks to 0xee5d90/0xee5d34.
  These methods read a vehicle proxy at CPxyVehicle+0x3728 via getters
  0x23ba714 / 0x23ba750. Each getter checks proxy state and then copies a
  cached byte at proxy+0x79 / proxy+0x78 respectively. The device rejects
  values above 100 or unavailable values by returning 255.
- Device initialization at 0xee56d8 obtains CPxyVehicle and subscribes to
  proxy events through delegate registration at vehicle+0x36e8,
  vehicle+0x3774 and vehicle+0x5010. The first two are consistent with
  the established proxy delegate-list offset +0x4c for proxies at
  +0x369c and +0x3728. Exact notification routing has not yet been traced.
- A separate device callback at 0xee54ac reads instrument-scale codes from
  CPxyVehicle+0x369c and updates device fields +0x78/+0x7c. The gauge values
  and scale selection therefore travel through distinct paths here.
- Separately, libhmiremoting.so exposes `engine.torque` and
  CCdsPropertyEngineTorque. Its factory at 0x1efbe4 attaches to
  CPxyVehicle+0x4584 (CActualValueTorque2); onStatus at 0x20827c formats
  `{"torque":%hd}` after decoding/converting that proxy's value. This is
  a different proxy from the Sports Displays gauge source. No live bind,
  valid torque samples or agreement between these paths has been tested.

The physical relationship is:

`power_kW = torque_Nm × engine_RPM / 9549.3`

Road speed alone is insufficient to establish engine torque or power.
This formula does not prove that the head unit performs that calculation.
The traced display consumes separate normalized inputs; their upstream
calculation, origin and physical accuracy remain unverified. Inverting
rounded gauge values would not establish reliable live RPM.

## Implication and next investigation

The Sports Displays device is an additional existing native consumer worth
tracing alongside the CDS RPM work. Next, identify the concrete proxy types
at vehicle+0x369c/+0x3728, their status decoders and notification source,
then determine whether their upstream path shares an engine-speed signal.
Do this offline before designing another bounded vehicle observation.

These findings do not demonstrate that opening Sports Displays binds
`engine.RPMSpeed`, that this proxy carries RPM, or that live RPM retrieval
has succeeded. The pause on plugin activation and standalone load/unload
probes remains in effect. No coding change or firmware modification is
proposed.

## Source identity

- HmiMain3D: 58795504 bytes, SHA-256
  `027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf`.
- libhmiremoting.so: 7169308 bytes, SHA-256
  `f5e0c7e78bc7054b96817064b7cd9cc6502e103759bab63a56a0320693aa1d37`.

Addresses are ELF virtual addresses for these captured files. No BMW
binary or captured live values are included in this checkpoint. This was
static analysis; no new application code or tests were introduced.
