# Return to the plugin-loading blocker — 26 November 2026

The owner returned to Ubuntu after the inert held-descriptor trial. All six
reported working-tree hashes match the retained reviewed files: full RPM
source/binary, initialization-only source/binary and both donor framework
link inputs. The VM IPv4 at this checkpoint is 192.168.8.157. No source was
edited, rebuilt, deployed or executed for this review.

The goal is to resume native RPM testing through a stable HMI initialization
path. Further dummy-file sizes are not the next priority. Today's result
is an offline dependency/initialization evidence gap, not a crash fix.

## Two distinct observations

1. The old standalone C loader probe loaded the prior candidate and found
   pluginAppInfo, then faulted on shutdown. The [17 November core analysis](2026-11-17-checkpoint.md)
   reconstructs QNX stream destruction entering GNU ios_base destruction,
   followed by an invalid delete input. The associated full-unit restarts
   still lack a proven causal/recovery explanation.
2. The earlier discoverable HMI candidate never produced an observed custom
   library mapping or application log. That does not identify the failing
   stage or prove it suffered the standalone shutdown fault. Its successful
   rollback and later registered-path observation are separate evidence.

Those must not be collapsed into one diagnosed failure. A standalone load
is not the real HMI context, and an expiring discovery endpoint cannot
unload code or repair a C++ ABI/binding fault after loading.

## Native loader and lifecycle comparison

The original HmiMain3D static path separates these stages:

| Stage | Original ELF call sites / fields | What remains unknown on the car |
| --- | --- | --- |
| Directory scan and manifest record | 0x2439ee0 → 0x2439860 → 0x24395d4 → 0x2439264 | Whether the earlier custom manifest completed scanning and was retained |
| XML/admission/description/code fields | 0x243c424; success 0x243c984 | Which step passed or failed for the earlier candidate |
| Connector and library load | 0x243ca7c; 0x243ceb4 | Current-scope connector success, dependency resolution and constructor behavior |
| pluginAppInfo lookup | 0x243cfd8; create +0x10, destroy +0x14 checks at 0x243d00c..0x243d020 | Actual HMI lookup not observed |
| Application construction | 0x243acbc; indirect create 0x243addc | Constructor/binding/data ABI and returned instance not observed |
| Later lifecycle | manager 0x24384e4 calls init 0x243ca54, create 0x243acbc, lifecycle 0x243aae8, then 0x243a564 | Stable native initialization not demonstrated |

These addresses describe static control flow, not addresses to call or write
on the car. Source follows the reviewed interface: primary PluginApp table
has 34 matching donor/native symbolic slots; overrides 21/22/23 match
onError/onInit/onFinalize. Native entry-point create/destroy offsets match
the candidate. These checks were already established by the earlier
interface audit; they do not validate every object layout or native binding.

Both the stock CoreFramework loader and failed probe pass numeric dlopen
flags 0x202. Changing those flags is not a supported fix based on this evidence.
The native path obtains IHmiContext and IHmiProcUnit when constructing its
local connector, unlike the isolated C probe's context.

The manager's diagnostic wrapper at 0x243daa4 passes severity 1 into
0x243d93c. That case tests the OTF logger flags (bit 0x04) before OTF_trace
at 0x243d9a8; it is not a direct sloginfo emission. Therefore the earlier
empty sloginfo grep cannot establish that no loader error was produced.
No logger configuration is changed or new target command prescribed here.

## Specific runtime-dependency gap

The [ELF audit metadata](evidence/2026-11-26-runtime-context-audit.json)
records hashes, DT_NEEDED edges and selected stream/allocation symbols for
the existing HMI, frameworks, both runtimes, candidates and original probe.
All were read as files; nothing was loaded or run. The captured HMI defines
its own new/delete functions and a 140-byte GNU cerr COPY object; the C probe
has a different executable symbol context. This cannot be reduced to changing
a library path or assuming the standalone load reproduces the HMI bindings.

The old probe core lists libecpp-ne.so.4. Neither the actual AppFramework,
CoreFramework, captured GNU libstdc++, initialization candidate nor C probe
directly names it in DT_NEEDED. The provider introducing it and resulting
resolution/initialization order are still untraced. A transitive dependency
or a dynamic load outside these known direct edges remains possible.

Eight libraries mapped in that core have no corresponding uploaded file:

- libhmibase.so
- libbacktrace.so.1
- libsocket.so.3
- libBMWOTFapi.so.3
- libboost_filesystem.so
- libboost_system.so
- libboost_regex.so
- libm.so.2

They are missing evidence, not proven faulty libraries. Their inclusion in
the core's list does not prove which one imports or loads the second runtime.
The existing HMI also has many dependencies outside this small core set;
this is a focused probe-dependency investigation, not a complete HMI audit.

## Next concrete step

Check whether those eight vehicle copies already exist on Ubuntu, within
the owner's existing data folders. First return paths only. SDK/donor copies
must be distinguished from files actually copied from this car; basename
alone does not establish provenance. No project/library replacement, Docker
change or compiler installation is needed for that inventory.

If absent locally, record the exact missing files for a later read-only
collection; do not run another loader probe to recreate the core. Inspect
actual dependencies and stream/symbol references offline before proposing a
source/linking change or a concrete native-host initialization/recovery trial.
The initialization-only candidate and earlier hidden stages stay unchanged.

The successful dummy expiry case and 50 host supervisor checks remain valid
within their scope. Emergency timer paths, HMI-only recovery/unload, stable
plugin initialization, CDS callbacks and changing live RPM remain unverified.
Actual plugin/HMI activation and standalone loading tests stay paused.
