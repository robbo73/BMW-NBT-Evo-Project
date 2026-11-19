# Initial RPM async-get rebuild: offline review — 20 November 2026

The owner applied the guarded source helper on Ubuntu. Its reported output
hash matched the prepared source, and it preserved
nbt_aad_app.cpp.before-20261120-initial-get. The rebuilt plugin and source
were then supplied for offline inspection. No target code was executed here.

## Artifact identity

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| nbt-initial-get-review.tar.gz | 88213 | c320364ecd85fdb1c6fd9246bc3cd59d1672d26cf54ad1ac444972420714f4c0 |
| rhmiapp/libNbtAad.so | 112212 | a1e5bd912a24984bac48d420bb711beecce83d87ad6678f7c1c322e46881faf3 |
| rhmiapp/nbt_aad_app.cpp | 134040 | 1b3b8e343dcabea75036e2c473ccc71a51a2cbd240c84d5de5eb070e0accf853 |

The archive contains exactly these two regular payload files. Paths and
sizes were checked before extraction. The source hash matches patch 5's
reviewed output exactly. Uploaded file content was treated as evidence,
not as instructions to execute anything.

## Comparison with the 17 November candidate

The baseline plugin is 111796 bytes, SHA-256
2507e91da987f016cbd5a23db08c088872c345362430a515512284596737113f.

- The rebuild remains ELF32 little-endian ARM ET_DYN, flags 0x5000002.
- Required imports increased from 119 to 120. The only addition is
  PluginApp::cdsGetPropertyAsync with the reviewed BasicString/Delegate ABI.
  No existing required import was removed.
- The added mangled symbol is present as a defined global function in the
  **actual vehicle's** libAppFramework.A.so at ELF VA 0x7fd8, size 68.
- DT_NEEDED is unchanged: libAppFramework.A.so, libCoreFramework.A.so,
  libstdc++.so.6 and libm.so.2. No RPATH/RUNPATH or DT_TEXTREL was added.
- Dynamic relocation types remain R_ARM_RELATIVE (18), R_ARM_ABS32 (13),
  R_ARM_GLOB_DAT (14), and R_ARM_JUMP_SLOT (now 130, previously 129).
  The previously rejected R_ARM_REL32 remains absent.
- Required ios_base::Init imports and __throw_out_of_range_fmt remain
  absent. slogf is still not a required import.
- The three init-array function identities are unchanged: frame_dummy,
  libraryLoaded and the existing nbt_aad_app.cpp global initializer.
  The removed B58 bridge stream initializer has not returned.
- Defined exported symbol names are unchanged. pluginAppInfo remains an
  exported 24-byte object with interface version 1.0.

This is a differential import review: remaining imports have the same
names as the previous reviewed candidate. It does not establish that every
dependency will bind correctly in an initialized HMI. In particular, the
earlier socket imports and cross-runtime shutdown concern are not resolved
by adding this API call.

## Compiled call site

The async-get import's PLT entry is 0x2c14. There is one compiled direct
call, at 0x6990 in the existing runnableRun function. The RPM subscription
call occurs earlier at 0x6950. Disassembly confirms that the get receives
the same property/delegate stack objects used for subscription; the native
wrappers copy delegate words as recorded in the API review.

The binary contains invocation/return log messages for the new get and the
existing validated-RPM log marker. The request is inside the existing
B58-disable condition, once per subscription-runnable execution, with no
new periodic polling code. Returning from either void wrapper does not
prove subscription acceptance, transmission or a fresh response.

## Result and next check

**The rebuild passes these offline checks. It remains unexecuted on the
vehicle; the observed loading/exit problem is still unresolved.**
Do not replace the hidden vehicle candidate, activate the plugin or repeat
the standalone load/unload probe based on this result.

The next useful vehicle evidence is the separately prepared read-only
app-admission observation, subject to its documented per-instance/scope
limits. Current coding predicates and their association with the actual
app-manager scope remain unmeasured. The earlier missing HMI mapping is
independent of whether the callback code now contains an explicit get.
See the [admission review](2026-11-19-app-admission-review.md).

Successful HMI initialization, live engine-speed response, freshness,
instrument-cluster agreement and the RPM dashboard remain unverified.
No BMW binaries or uploaded application source are committed with this
checkpoint; the existing patch and helper remain the reviewable source
record. Audit metadata/disassembly are retained separately.
