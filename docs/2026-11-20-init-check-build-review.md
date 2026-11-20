# Initialization-check build: offline review — 20 November 2026

The owner's Ubuntu build completed with the previously seen signed/unsigned
warnings. Its printed hashes confirmed that the full RPM source and full
RPM binary were unchanged. The uploaded review archive was inspected as
data; no uploaded or ARM program was executed.

## Verified identity

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| nbt-init-check-review.tar.gz | 58781 | f25a0f842103020edfdf3550779716c2d8a48e45799b833abd15f106db146b9b |
| libNbtAadInitCheck.so | 43757 | 9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d |
| nbt_aad_app_init_check.cpp | 131728 | d742b624263cc16f30d7809d942e6ac1e5267466fa312db985977f9a3dc3c776 |

All three match the owner's reported hashes. The archive contains exactly
the two expected regular source/binary files; member paths and sizes were
checked before extraction. The source matches the guarded generator output.

## Binary findings

- ELF32 little-endian ARM ET_DYN, EABI flags 0x5000002.
- Distinct SONAME libNbtAadInitCheck.so. The full libNbtAad.so is separate.
- Required imports fall from 120 in the full RPM build to 66, with no new
  required names. All 66 names have defined exported providers in the
  captured vehicle framework/runtime/libc files. This checks availability
  of names, not runtime binding order or complete ABI compatibility.
- No CDS subscription/async-get, PluginApp::post, action-registration,
  socket/send/receive, spawn or kill import remains in this build.
- DT_NEEDED remains AppFramework, CoreFramework, libstdc++.so.6 and libm.so.2.
  No RPATH/RUNPATH or DT_TEXTREL. Dynamic relocations are RELATIVE (11),
  GLOB_DAT (12), JUMP_SLOT (76); no rejected R_ARM_REL32.
- Required slogf, ios_base::Init and formatted out-of-range imports remain
  absent. Existing optional logging still uses the captured logger code.
- The init array has frame_dummy, libraryLoaded and the check source's
  existing global initializer. No bridge stream initializer was reintroduced.
- pluginAppInfo is 24 bytes, version 1.0, with create/destroy pointers
  resolving to the compiled createApp (0x2838) and destroyApp (0x27e4).

Disassembly verifies appOnInit at 0x2a34 (64 bytes): local logging calls and
one external call, the actual PluginApp::onInit. appOnFinalize at 0x29fc
(56 bytes) logs, clears the app's global runnable pointer and calls the
native base finalizer. Neither schedules telemetry or Android Auto work.
createApp retains the reviewed native constructor/vtable setup. destroyApp
retains normal deletion through the native deleting-destructor slot; no
exit-cleanup bypass was introduced.

The library constructor and existing global construction still run. The
bridge translation unit remains linked, although this lifecycle override
does not initialize it. This binary is not freestanding, a working dashboard
or a proof that native HMI loading/unloading will be stable.

## Frozen prospective trial payload

A separate five-file payload was assembled **offline only** under the name
NbtAadInitCheck. It uses this reviewed binary and the already reviewed
NbtAad.xml/text/image assets. The manifest name and library basename were
changed to NbtAadInitCheck; resource names and contents are unchanged.
Manifest/XML parsing, resource references, original asset hashes and ZIP
integrity were checked. No payload was copied to the BMW.

The prospective manifest retains autoStart=yes and connector id 210.
Exposing it in a registered Plugins directory would therefore enable
automatic loading; simply calling it a check does not make exposure inert.
The existing hidden NbtAad candidate must remain hidden and any live ID/name
conflicts must be checked before a future trial.

| Payload file | Bytes | SHA-256 |
| --- | ---: | --- |
| libNbtAadInitCheck.so | 43757 | 9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d |
| NbtAadInitCheck.manifest | 586 | c74b96f7b9b36afbe71ef8b83b1eda5f162fdb388fb6ac6acb7c6a5243c9ae43 |
| NbtAad.xml | 10951 | 4a84717f83cee07e1f52cea95ddef932428e7c5470ee9227789dd045558d25e4 |
| NbtAad_ALL_Texts.zip | 7487 | 2b3ad02ec34cc476f53539070e5da7d9da4143ce75452e94499ad536532ad14b |
| NbtAad_ALL_Images.zip | 55671 | 38539939b8cf14343176e765d82144447918e6f26298f813fa6597381537047c |

Candidate archive: 85888 bytes, SHA-256
a564109d08fdcbd71b232f8ac79fbe20f2e3dcd394017a7308c9c4f7099b8018.
It is retained separately, not committed as a binary or deployed.

## Result and next step

The initialization-check build passes these offline checks. No additional
Ubuntu rebuild is needed for this reviewed variant. The next preparation
is a pinned hidden-stage/read-back procedure and the exact recovery check
for this trial, following the [draft trial plan](2026-11-20-init-check-trial-plan.md).
Those must precede any exposure to the loader. The vehicle-execution pause
remains in place, including the standalone dlopen probe.

Successful native initialization, process stability and normal finalization
remain untested. A future pass would establish only those observed lifecycle
stages, not CDS, RPM, cluster agreement or Android Auto features. Full source,
ELFs, payloads, annotated disassembly and audit metadata are retained outside
Git; this checkpoint commits documentation only.
