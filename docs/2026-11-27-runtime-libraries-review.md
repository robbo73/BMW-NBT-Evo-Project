# Captured runtime dependencies — 27 November 2026

**The missing dependency edge is now identified:** the captured
`libBMWOTFapi.so.3` directly requires QNX `libecpp-ne.so.4`. AppFramework,
CoreFramework and hmibase require that OTF library, while also requiring GNU
`libstdc++.so.6`. Both C++ runtimes are therefore included by the focused
candidate dependency graph without a separate unexplained dynamic load.
This identifies inclusion, not the binding/initialization error or a crash fix.
Plugin loading, HMI activation and standalone loader tests remain paused.

## Collection and integrity

The owner copied eight existing files read-only from hu-omap through the
hu-jacinto SSH connection. No library was replaced, loaded or executed.

Archive `nbt-runtime-libs-9yrkc0ke.tar.gz`, 724320 bytes, SHA-256:

```text
f66bcbac817b622b69850708c6721572f501483b464d4a78ddc9911c46f3d563
```

Offline checks passed: exact archive hash; nine unique ordinary members;
eight expected library names and sizes; all owner-generated per-file hashes;
and ELF32 little-endian ARM headers. The libraries total 1943777 bytes.
The [audit metadata](evidence/2026-11-27-runtime-libraries-audit.json) preserves
the manifest, hashes, direct dependencies, selected symbols and static sites.
Raw BMW libraries and the core remain outside this repository.

| Captured file | Bytes | Direct dependencies |
| --- | ---: | --- |
| libhmibase.so | 397192 | backtrace, socket, BMWOTFapi, three Boost libraries, GNU libstdc++, libm, libc |
| libbacktrace.so.1 | 17700 | libc |
| libsocket.so.3 | 187592 | libc |
| libBMWOTFapi.so.3 | 34218 | **libecpp-ne.so.4**, libc |
| libboost_filesystem.so | 99956 | boost_system, GNU libstdc++, libm, libc |
| libboost_system.so | 13855 | GNU libstdc++, libm, libc |
| libboost_regex.so | 1036592 | GNU libstdc++, libm, libc |
| libm.so.2 | 156672 | libc |

These are the OMAP files. Their sizes must not be replaced with the earlier
Jacinto socket-library observation or SDK/donor copies.

## Dependency and export results

The eight additions close the DT_NEEDED graph for the historic crashed
candidate, current RPM candidate and initialization-only candidate. Each
closure contains the same 13 captured libraries. There are no missing
DT_NEEDED targets within those closures. All 13 library basenames also match
the old probe core's library list, and every captured PT_DYNAMIC virtual
address matches the corresponding core link-map dynamic offset. Offset
agreement supports consistency; it does not prove full historical byte identity.

| Candidate | SHA-256 | Required GLOBAL imports | Without a named export in its captured closure |
| --- | --- | ---: | ---: |
| Historic loader-fixed | ac246b424e39a0ca9904f60ae900c01d68daee2e489496cfbb9464cef4534721 | 121 | 0 |
| Current RPM | a1e5bd912a24984bac48d420bb711beecce83d87ad6678f7c1c322e46881faf3 | 120 | 0 |
| Initialization-only | 9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d | 66 | 0 |

The 13 libraries' own required GLOBAL imports also have named providers in
this captured set. In particular, `recv`, `sendto` and `socket` are exported
by the actual OMAP `libsocket.so.3`, closing the earlier socket-provider gap.
No `slogf` export appears in this focused set; the reviewed candidates already
removed its required import and use guarded optional lookup. Nothing is
added or changed as a consequence of that observation.

These are symbol-name/export checks, not successful relocations. They do not
verify loader search order, symbol versions, object layouts or runtime ABI
compatibility. The full HmiMain3D dependency graph is much larger and remains
incomplete; a complete small probe graph is not a complete HMI audit.

## Stock stream initialization remains relevant

The prior source cleanup removed our two unnecessary stream initializers.
The new stock library evidence shows why that alone cannot establish that
no stream initialization occurs in the candidate's dependencies:

- `libhmibase.so` imports the same `std::ios_base::Init` constructor and
  destructor names that both C++ runtimes export. Five checked init-array
  routines call the constructor PLT at `0x1aa18`, then register a destructor
  through `__aeabi_atexit`. Entries are `0x42e90`, `0x43698`, `0x487f8`,
  `0x4d43c` and `0x4fedc`; exact call sites are recorded in the audit.
- QNX `libecpp-ne.so.4` has a stream initializer at `0x14e44`. Its GOT
  references identify `std::cout`, the QNX ostream vtable and the QNX
  ostream destructor. The path stores the vtable at `0x14f14` and registers
  the destructor through `__aeabi_atexit` at `0x14f34`.
- Both runtimes export `std::cout` and identically named ios_base
  initialization/destruction functions. Their cout objects remain different
  sizes: GNU 140 bytes, QNX 52 bytes. The earlier core independently
  reconstructs QNX stream destruction entering GNU ios_base destruction.

These are static constructor paths and symbolic references. They do not
establish which provider each reference actually resolved to or the order
in which all initializers ran. Of 53 selected relocation slots checked
across the mapped images, none is retained in the core's stored bytes.
Omitted pages must not be read as zero or used to invent GOT targets.

The OTF library's direct DT_NEEDED edge is enough to introduce QNX C++ even
though its selected undefined symbols contain no `std::` stream import.
Do not infer that removing an application stream include removes the
transitive runtime, or that the stock OTF library is defective.

## Consequence and next work

The [26 November evidence gap](2026-11-26-runtime-context-review.md) is now
closed for these eight files and the introducing dependency. No new source
patch, rebuild, runtime replacement, library-path change or vehicle trial
follows from the result.

The next question is actual symbol binding and initialization context in
the native HMI versus the standalone C probe. Existing HMI evidence includes
its own allocation functions and GNU-sized stream COPY data; the C probe
has a different executable context. An offline loader/symbol-resolution
analysis can now use the complete focused graph and checked constructor
sites, while explicitly accounting for dependencies still missing from the
full HMI graph. An assumed search order is not a measured binding result.

The earlier HMI non-loading observation remains a separate discovery/admission/
construction investigation. The cause of the associated whole-unit restarts
is not established by a DT_NEEDED edge. Stable native initialization, live
CDS callbacks and live RPM remain unverified. The successful inert RAM and
held-descriptor trials retain their original limited scope.
