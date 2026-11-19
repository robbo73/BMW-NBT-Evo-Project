# Actual vehicle coding library and app admission — 19 November 2026

The owner copied libhmicoding.so from the existing hu-omap firmware. The
uploaded archive contains one regular file: 916424 bytes, SHA-256
`f9a6d68e55b006229792d1b4bb417378dabc503076044fa574a810cd61a45e85`.
Both match the Chromebook's size/hash output. The original ARM/QNX ELF was
inspected offline and remains unchanged. No vehicle code was executed.

## Exact gate and meanings

HmiMain3D's CSpecialAppsHelper admission method at 0x1019dc0 returns true
when variant 0x1a0 is set; otherwise it returns variant 0x9c56. The actual
CHmiVariantServer vtable's +0xc slot resolves to isVariantSet at library
ELF VA 0x47708. Its dispatch places 0x1a0 in the direct VA-coded range and
0x9c56 in the derived EVA range.

The captured coding descriptors give the following **active** predicates.
Names and byte/mask selectors describe this firmware; they are not observed
current settings or instructions to edit coding.

| VA ID | Exact predicate name | Page | Byte | Mask | Required extracted value |
| --- | --- | --- | --- | --- | ---: |
| 0x1a0 | va_A4A_REMOTE_APPS | 0x3000 | 0x6c | 0x01 | 1 |
| 0x19d | va_A4A | 0x3000 | 0x6b | 0x80 | 1 |
| 0x19a | va_REMOTE_HMI | 0x3000 | 0x6b | 0x70 | 1 |
| 0x00b2 | va_TOUCH_COMMAND | 0x300b | 0 | 0x01 | 1 |
| 0x00f4 | va_SPECIAL_VEHICLE_security | 0x3000 | 0x18 | 0xc0 | 1 |
| 0x00f5 | va_SPECIAL_VEHICLE_authority_marked | 0x3000 | 0x18 | 0xc0 | 2 |
| 0x00f6 | va_SPECIAL_VEHICLE_authority_unmarked | 0x3000 | 0x18 | 0xc0 | 3 |

The library has distinct `_nicht_aktiv` descriptors. Their names must not
be substituted for the active IDs above based on another firmware's notes.

Derived 0x9c56 dispatches to 0x46b98. It ORs cached IVA predicates 0x4e55,
0x4e54, 0x5264, and derived 0x9c55. The last is a special-vehicle predicate
combined with role value 1. Initialization establishes these inputs:

- IVA 0x4e55: direct VA 0x19a.
- IVA 0x4e54: direct VA 0x19d OR 0x1a0.
- IVA 0x5264: direct VA 0x00b2.
- IVA 0x5142/0x5143/0x5144: the three special-vehicle predicates.
- EVA 0x9c55: any of those special-vehicle IVAs AND role == 1.

Native EVA evaluation reads the cached IVA entries; the observer must not
replace them with guessed values from static defaults. The direct 0x1a0
check reads its VA descriptor/coding buffer through the instance's VA map.

## Read-only observer prepared

The explicit `--inspect-admission` option requires `--read-cache`. It uses
the existing SSH/pidin/dd transport and introduces no target executable,
library load, native API call, registry creation or coding write.

The observer discovers libhmicoding's current mapping and checks six small
code fingerprints: the HMI admission method, coding dispatcher, derived
predicate routine, direct coded-value check, IVA accessor and VA map lookup.
It then walks the existing IHmiVariantServer registry cache, verifies each
CHmiVariantServer type, and reads role, the direct 0x1a0 predicate and the
six relevant cached IVA entries. A missing VA descriptor or unavailable
coding buffer is distinguished from an available buffer selecting zero.

The direct VA check follows CVACoding::isCodingFeature at 0x51d48: validate
descriptor identity/data length, obtain the selected byte, apply its mask
and shift, then compare with the expected value. The runtime VA hash map is
at server+0x34. IVA entries are at server+0xa4, 8 bytes per entry indexed
from 0x4e20; role is at server+4. These layouts were checked in the actual
library's constructor/accessors, not imported from the emulator profile.

Results are per observed variant-server instance. The association between
an observed cache scope and the app manager's execution scope has not yet
been established. Even a passing predicate is not proof of later manifest,
connector, symbol resolution, app initialization or CDS subscription success.
Every reported dynamic region is rechecked using the existing best-effort
snapshot mechanism; this does not make the view atomic.

The default cache interface remains ICarDataServer. The registry helper now
also accepts an explicit printable ASCII interface name so the new mode can
inspect IHmiVariantServer without calling a lookup API. Mapping reports may
also include a discovered coding-module base. Mappings-only mode continues
to request zero process-memory reads.

All 71 offline tests pass. Added cases cover independent gate branches,
special-vehicle role requirements, unpopulated IVA entries, missing/short
coding data, wrong descriptors/types, mutation, cycles, fingerprint mismatch,
missing module mapping and explicit mode selection. No current coding values
have been measured on the vehicle with this new mode.

## Remaining questions

The tested RPM provider had no RPM property entry with the engine off or
idling, while its **function-block readiness** state was 2. That does not
answer this separate **app-admission coding** question. A future read-only
observation can measure these predicates; there is no reason to reconnect
solely for this offline review.

The new observer does not relax the pause on plugin loading or standalone
load/unload probes following the earlier crashes. The actual car's current
admission values, successful native subscription and fresh B58 RPM remain
unverified. No firmware, patched binaries or vehicle coding data are committed.
