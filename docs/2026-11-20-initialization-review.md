# Native initialization and separate check build — 20 November 2026

The owner resumed on Ubuntu after completing the read-only admission and
manager-path checks. Those observations support the expected native loader
configuration; they do not establish that an application object was created
or its lifecycle callback ran. The latest full RPM build remains 112212
bytes, SHA-256 a1e5bd912a24984bac48d420bb711beecce83d87ad6678f7c1c322e46881faf3.

## Framework lifecycle checked in the actual car library

The captured libAppFramework.A.so has SHA-256
057618b81375564f5255308a3c59111dd1e9eb57e43e38b7a858bff04ab41ce5.

- PluginApp::init at 0x50bc checks the state word at object+0x10c. For
  state values 1 or 2, it dispatches virtual +0x58, primary slot 22.
  Other states return false before calling the override.
- Base onInit at 0x5114 simply returns true. Therefore a speculative guard
  around a false result from this particular base method would not explain
  the missing plugin, and no such patch was made.
- PluginApp::finalize at 0x50ec permits states 1 through 3 and dispatches
  virtual +0x5c, primary slot 23. Base onFinalize at 0x5124 returns directly.
- The actual HMI's XML-only app creation path allocates 0x160 bytes before
  calling the same native PluginApp constructor. Our existing source
  allocates 0x200 bytes and copies the previously reviewed 34-slot primary
  vtable. No increase in object storage or speculative slot change is
  supported by these findings. This is not a complete ABI/lifetime proof.

ManagedPluginApp::init at HMI 0x243ca54 obtains a connector, prepares its
parameter bundle, resolves the library path, loads the library, looks up
pluginAppInfo and validates its create/destroy pointers. Success advances
the managed record to state 2. This operation alone is not the application's
onInit callback. The separate create path at 0x243acbc calls the entry's
create pointer at 0x243addc on the reviewed fallback path, retains the app
pointer at managed+0x64 and advances to state 3. Native context callbacks
can also participate; all later scheduling/registration is not yet audited.

The loader's dynamic-load failure path calls dlerror at 0x243cee8 and
includes that text in its message. Its output goes through the existing gated OTF/error sink
at HMI 0x243d93c. An empty sloginfo filter is not evidence that no failure
occurred, and changing platform logger configuration is not proposed.

## Separate initialization-only source

The helper prepares rhmiapp/nbt_aad_app_init_check.cpp from the exact
reviewed full RPM source. It does not edit rhmiapp/nbt_aad_app.cpp.
The separate build output is rhmiapp/libNbtAadInitCheck.so, with a distinct
SONAME. It does not overwrite rhmiapp/libNbtAad.so.

The generated variant retains the same native constructor, vtable setup,
entry ABI, normal destructor and existing library logging. Its appOnInit
override only logs entry, calls the native base onInit and logs its result.
It registers no application actions or CDS handlers and posts no startup
or polling runnable. Its finalizer logs and invokes the native base method;
it does not shut down an unstarted B58 bridge.

The banner identifies init-check-1. This is a diagnostic variant, not a
working dashboard or a replacement Android Auto release. Other unused source
functions remain in the generated copy, and the existing bridge translation
unit is linked. Compiler elimination and the resulting imports/call sites
must be checked in the rebuilt ELF. Existing global construction and native
framework dependencies still run when loaded; this is not an isolated or
zero-risk runtime.

Input full-source SHA-256:
1b3b8e343dcabea75036e2c473ccc71a51a2cbd240c84d5de5eb070e0accf853.

Generated separate source: 131728 bytes, SHA-256
d742b624263cc16f30d7809d942e6ac1e5267466fa312db985977f9a3dc3c776.

The helper checks both hashes, uses exclusive output creation and refuses
a different existing check source. Matching existing output can be verified
without rewriting it. A local matching-copy exercise confirmed check mode
made no file, generation left the full source unchanged, output matched
the reviewed bytes, repeated verification was harmless, and a modified input
was refused. Bash syntax checking passed. No QNX build was run in the cloud.

The build script follows the existing qcc ARMv7/gpp shared-library recipe,
suppresses expected unused-function warnings for the reduced override and
uses the new source/output names. It refuses an existing check binary or
review archive. It prints full/check source and binary hashes and creates
~/nbt-init-check-review.tar.gz for offline review only. It contains no SSH,
installation, reboot or platform-configuration operation.

## Recovery and observation plan for a later native-host trial

This package stops at source generation, compilation and offline inspection.
After the new ELF is reviewed, prepare a separately named frozen stage and
matching manifest/resources; do not replace the older hidden stage or the
full RPM binary. No staged artifact or manifest for that trial is supplied
by this source-preparation package yet.

The later procedure must identify the exact active/hidden trial paths and
hashes, verify a working SSH route and rollback before exposure, and record
baseline HMI identity and logs. The first native-host trial should seek only
the library-loaded, create and INIT CHECK onInit markers while observing
HMI stability. It must not use the standalone C dlopen probe.

Rollback must remove the trial from discovery before another startup while
preserving its files and logs. A directory rename is not an unload operation
and cannot stop code already executing in HMI. Recovery timing and what to
do if SSH is unavailable must be reviewed explicitly before activation; the
previous successful file rollback does not prove recovery from every fault.
No factory libraries, startup files, watchdog settings or firmware keys are
part of this plan.

This preparation does not lift the vehicle-execution pause. A successful
future initialization-only trial would not validate CDS, RPM, Android Auto
features, process shutdown or all unload paths. The full candidate and live
engine-speed work remain separate subsequent steps.
