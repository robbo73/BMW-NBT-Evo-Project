# Read-only runtime binding observer

This Python 3 client observes selected existing pointers in the stock
HmiMain3D process on hu-omap. It runs on Chromebook Linux or Ubuntu, using
the unchanged SSHMemory transport from `../native-cache-reader/`.
It installs no BMW executable and does not load a library, invoke a native
method, change a pointer or signal HMI. This is not a CDS client or RPM test.

## Why this observer exists

The historic C-only dlopen probe faulted during mixed C++ stream destruction.
The dependency graph now explains why GNU libstdc++ and QNX libecpp are
loaded together. The core does not retain the relevant GOT pages. The real
HMI has a different executable context, including allocation functions and
a GNU-sized cerr COPY object. A hypothesis about loader order is insufficient
to determine its actual bindings.

The frozen profile describes 27 R_ARM_GLOB_DAT/JUMP_SLOT pointer slots in
HMI, GNU C++, QNX C++ and hmibase, plus 35 selected named definitions.
It also records seven stream-storage first words, including the HMI cerr
COPY object. A COPY relocation is object storage, never a pointer slot.
Five small code/header fingerprints are checked before and after observation.
All offsets and hashes were derived offline from the retained vehicle files.
No BMW binary bytes are distributed in this directory.

## Offline preparation on Ubuntu

No compiler, SDK, Docker, pip package, root access or vehicle connection is
needed. From the repository root:

```sh
python3 -B -m unittest discover -s tools/runtime-binding-reader -p 'test*.py' -v
```

The separate frozen preparation includes `run_host_review.sh` at its root.
Running it checks source pins, executes the 16 new observer tests and 89
unchanged cache-reader tests, and saves host logs plus an explicitly synthetic
observation in a fresh local directory/archive. It never instantiates a real
SSH transport. The synthetic observation is not a vehicle capture.

## Later vehicle observation

Native execution of this new observation mode has not been verified. Obtain
a fresh HmiMain3D PID and use a new local output path for each invocation.
Default behavior collects mappings only with zero memory reads. It requires
GNU C++, QNX C++ and hmibase mappings. The inherited transport also verifies
HmiMain3D identity and the standard plugin/remoting mappings.

The explicit `--read-bindings` mode adds bounded reads after the fingerprints
match. The configured profile's successful synthetic path performs 78 reads,
808 aligned bytes; hard observer caps are 160 reads and 8192 aligned bytes,
inside the existing transport's limits. Values are read twice; a changed
binding or stream first word stops the result. These unlocked rechecks are
best-effort, not an atomic snapshot or process suspension.

Do not use an earlier session's PID. Missing modules, wrong fingerprints,
short reads or changed values must be preserved as a stopped report, not
worked around by editing offsets or forcing a library load. The vehicle
observation can be scheduled separately after the Ubuntu preparation.

## Interpretation

- Each pointer is compared to exact named addresses in the four captured
  module profiles. A match identifies an observed address, not a complete
  loader decision or ABI proof.
- A target inside a captured PLT range may still be a linker trampoline.
  The observer never invokes it to force resolution.
- Unknown or zero targets are reported without following them. They are not
  treated as successful symbol resolution or a reason to call target code.
- Only a configured stream object's first word is read. A match to a named
  vtable plus eight is reported as an address comparison, not validated
  construction history, object lifetime or compatibility.
- Snapshot completion is not a crash fix, plugin admission/loading success,
  initialization-order proof, callback/lifetime proof or telemetry validation.

The file-level SHA-256 values identify the analysis inputs; the client does
not hash each entire mapped library. The small fingerprints are consistency
guards, not full runtime image verification. Other HMI libraries are outside
this small lookup profile, so an unknown address can have a legitimate
provider outside it. Keep the actual plugin/loader-probe pause in place.
