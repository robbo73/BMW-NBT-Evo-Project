# Native RPM investigation and handover — 17 November 2026

**Vehicle library-loading tests and HMI activation remain paused after observed
head-unit restarts. Resume with offline work on Ubuntu.**

The objective remains native B58 RPM on iDrive, without Bluetooth/ENET equipment
in normal use. Live `engine.RPMSpeed`, direct DME communication and an RPM screen
have not been demonstrated. Even Realities G2 remains deferred.

## Today's result

An existing crash core identifies a cross-runtime C++ shutdown path in the
standalone probe. A source cleanup removes unnecessary stream initialization
from our plugin, and the owner rebuilt it successfully. Static review confirms
the intended changes. The new binary has not been executed on the BMW.

The earlier discoverable candidate remains rolled back to its disabled stage:

```text
/var/opt/hmi/data/ID5/.nbt-rpm-stage-09902c834a37
```

`HmiMain3D` on `hu-omap` remains the intended HMI context. No custom plugin
mapping, application initialization, CDS callback or changing RPM value has
been observed there. The diagnostic application is a separate process.

## Startup-object comparison

The existing Docker image includes SDK startup helpers identifying GCC 4.4.2
and custom GCC 4.9.4 helpers. `qcc` is a wrapper around the custom compiler;
changing its profile text does not select a different compiler.

Three offline links used one compiled C probe object and varied only the helper
search for `crtbegin.o`/`crtend.o`. Link maps confirm the selected objects. SDK
`crt1.o`, `crti.o` and `crtn.o` remained unchanged. No ARM program was executed.

| Variant | Result |
| --- | --- |
| Default GCC 4.9 nonshared helpers | Exactly reproduces original probe SHA-256 `372952e265abd04f08167aedd3463b6f32f45719d11c990d5e89410b77e4e8a1` |
| SDK GCC 4.4.2 helpers | Links; conditional `__cxa_finalize`, self-referential DSO handle |
| GCC 4.9 PIC/shared helpers in a non-PIE link | Links; also has conditional finalization and a self DSO handle |

This controls for helper mode as well as compiler vintage. It does not prove a
GCC-version fault or justify replacing the application's startup objects.
Captured libc already executes registered C++ destructors during normal exit;
absence of a helper's explicit finalization call does not establish skipped
cleanup. No alternative probe was run on the car.

## Existing crash evidence

Read-only inspection of `/var/dump` on OMAP found
`nbt_load_probe_372952e265ab.core`, 200704 bytes. The owner copied the existing
file without running another probe. The BMW original was left in place.

Core SHA-256:
`6b1fdf56fdab7a818aa5d34170f9da808c6a43643fbbf601bb008a06b4d05f25`.

Its link-map note identifies the earlier temporary plugin candidate
`libNbtAad_ac246b424e39.so`. This is a plugin-load-attempt core; it is not a
separate captured core of the later stock-framework-only control.

Registers and matching instruction sequences reconstruct this shutdown path:

```text
QNX libecpp-ne.so.4: std::ostream::~ostream()
    -> GNU libstdc++.so.6: std::ios_base::~ios_base()
    -> operator delete[] / libc __free(pointer = 8)
    -> load from address 4: SIGSEGV
```

The saved caller addresses match the destructor call sites in the captured
libraries. The saved object pointer matches GNU's exported `std::cout`.
This is a manual reconstruction from registers, stack frames and disassembly;
it is not a complete debugger-verified unwind. Some mapped pages, including
the stream object's data, are omitted from the core.

The owner copied the stock `libecpp-ne.so.4` for offline inspection. It and
GNU libstdc++ export the same `std::cout` symbol with different object sizes:

| Provider | `std::cout` size | Destructor implementation |
| --- | ---: | --- |
| GNU libstdc++.so.6 | 140 bytes | GNU ios_base layout |
| QNX libecpp-ne.so.4 | 52 bytes | QNX stream/ios_base layout |

The core and matching call instruction establish a cross-runtime destruction
path with an invalid delete input. The binding and initialization order that
produced the hybrid state remains unverified. The separate stock-framework-only
failure remains relevant, and the cause of the whole-unit restarts is not proven.

The stock HMI itself imports GNU stream initialization and contains a 140-byte
GNU `std::cerr` COPY object. Do not infer that both runtimes can never coexist
or that a C-only dlopen probe reproduces the established HMI process context.
No stock library, firmware, watchdog, startup configuration or HMI process was
modified during this collection.

## Source cleanup and reviewed QNX build

[Patch 4](../patches/0004-remove-unused-b58-iostream.patch) removes exactly two
unused `<iostream>` includes: one in `b58_telemetry.hpp`, one in
`b58_rhmi_bridge.cpp`. These headers added automatic stream initialization even
though the telemetry code uses no stream expressions. Parser logic, exception
handling, RPM validation and logging are unchanged. Normal cleanup remains.

The owner used the [guarded helper](../tools/prepare_stream_cleanup.py), which
checked both source hashes and created backups, then rebuilt only `rhmiapp`
using the existing `qnx65-armv7-toolchain:4.9` image and original flags.
**The cleanup is already applied; do not apply it again.**

| Item | Previous loader-fixed build | Latest stream-cleanup build |
| --- | ---: | ---: |
| libNbtAad.so bytes | 112222 | 111796 |
| Required dynamic imports | 121 | 119 |
| Init-array entries | 4 | 3 |
| Dynamic R_ARM_REL32 | absent | absent |
| DT_TEXTREL | absent | absent |

Latest binary SHA-256:
`2507e91da987f016cbd5a23db08c088872c345362430a515512284596737113f`.

Reviewed upload `nbt-stream-cleanup-review.tar.gz` SHA-256:
`bd9a07330d3603d721bc66802856f3d93742ef65245a00c8ea9c26bd5d2fc8da`.

Confirmed changes and retained checks:

- Both `std::ios_base::Init` constructor/destructor imports are removed; no new
  required imports appear. The bridge's automatic initializer is removed.
- All three source files match the prepared revision exactly; `nbt_aad_app.cpp`
  is unchanged from the preceding loader-fixed build.
- `pluginAppInfo` and the validated RPM log format remain present. The earlier
  required `slogf`, exception RTTI relocation and formatted range-error helper
  remain absent. Optional system logging is retained through `dlsym`.
- Direct dependencies remain AppFramework, CoreFramework, libstdc++.so.6 and
  libm.so.2. No RPATH/RUNPATH was added.
- As before, recv/sendto/socket are the only required imports lacking an
  independently captured provider; stock libsocket has not been audited here.
  This is not a new import regression or proof of a target load failure.

Host validation of the exact edited B58 sources passed 557 assertions, 2000
deterministic malformed/mixed inputs and 500 generated RPM payloads under
Address/UndefinedBehavior sanitizers with the old GNU string ABI. A host bridge
object comparison removed stream initialization with no imports added.
The QNX build completed with the existing signed/unsigned comparison warnings.
The earlier full Ubuntu/TSAN suite result remains historical; it was not rerun
for these include removals or this documentation update.

This cleanup removes avoidable initialization from our code. Framework
dependencies can still load both runtimes. It does not establish a fix for
standalone stock-framework loading, stable shutdown or vehicle execution.

## Resume here tomorrow

1. Start on the Windows PC with Ubuntu. The source in `~/milestone-7` already
   contains all four patches and the reviewed binary. No further rebuild is
   needed to validate today's two-line cleanup. VM addresses change; obtain
   the current address when transferring files.
2. Continue offline investigation of the real HMI's runtime/dependency binding
   and initialization context using the captured core, libraries and HMI file.
   Compare that context with the C-only standalone probe before considering
   further target execution. Do not bypass destructors with `_exit` or change
   system runtime/library order as an unvalidated workaround.
3. Investigate HMI plugin discovery separately. The earlier RW Plugins candidate
   was not observed loaded; registration/discovery and lifecycle initialization
   remain open even though the previous temporary dlopen found `pluginAppInfo`.
4. Reassess a concrete execution/recovery procedure after reviewing these issues.
   Keep standalone car probes and HMI activation paused. No further BMW data
   collection is requested for today's review.
5. Once native initialization is stable, verify real changing `engine.RPMSpeed`
   samples against the instrument cluster, then implement the RPM display and
   validate normal use without external adapters.

Preserve on Ubuntu: `~/milestone-7`, its source backups,
`~/nbt-startup-comparison-review.tar.gz`, `~/nbt-stream-cleanup-review.tar.gz`
and the existing toolchain image. The core/runtime collection archives were
created on the Chromebook and provided for offline analysis. RAM probe files
are volatile and must not be assumed present after a reboot.

This repository preserves documentation, source patches and preparation tools.
Raw cores, vehicle libraries, HMI binaries, compiler startup objects, built
plugins and vehicle logs remain outside GitHub. The full modified source and
Docker image are also held separately; this checkout alone cannot rebuild the
application. Environment setup was not republished or changed for this update.
