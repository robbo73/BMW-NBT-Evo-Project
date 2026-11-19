# Changes to the modified milestone-7 source

Patches 1–4 preserve the changes used for the 15–17 November 2026 native
RPM logging candidates. Patch 5 is a prepared 20 November source change,
pending an Ubuntu QNX rebuild and offline binary review. Apply them to the corresponding modified
`~/milestone-7` source, not to this documentation-only checkout.

**Vehicle library-loading tests and HMI activation are paused.** The latest
candidate is reviewed offline only. The previous candidate loaded in the
standalone probe, but exit faults and observed unit restarts remain unresolved.
These patches are source records, not a deployment
instruction or a claim of full vehicle compatibility.

1. `0001-b58-libstdcxx-compat.patch`: use the scanner-validated character range
   to construct a numeric token without the newer formatted range-error helper.
2. `0002-b58-validated-rpm-log.patch`: read and log accepted RPM, returning
   before reading when the incoming sample is rejected.
3. `0003-qnx-loader-compat.patch`: replace the typed telemetry exception catch
   with catch-all handling and resolve optional `slogf` through `dlsym`, retaining
   RAM/USB output. The reviewed rebuild removes the rejected dynamic
   `R_ARM_REL32` relocation, required `slogf` import and `DT_TEXTREL` flag.
4. `0004-remove-unused-b58-iostream.patch`: remove unused `<iostream>` includes
   from the telemetry header and bridge. The reviewed QNX rebuild removes both
   `std::ios_base::Init` imports and the bridge's automatic initializer, with no
   required imports added. This removes avoidable initialization from our code;
   it is not a verified fix for standalone stock-framework loading.
5. `0005-b58-initial-async-get.patch`: declare the existing native async-get
   method and invoke it once for RPM after the subscription call in the
   existing app initialization runnable, using the same callback. Logs mark
   invocation and return without claiming successful data delivery. This
   source change has not yet been QNX-built or vehicle-tested; see its
   [preparation review](../docs/2026-11-20-initial-get-preparation.md).

The supplied original source identifies NBT-AAD / nanaisu and
[Supra-iDrive6-Android-Auto](https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
and carries `SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0` and its
required copyright notice. These patches leave those source notices intact.
The complete upstream/modified application is not included here.

The 16 November rebuilt candidate contains patches 1–3; the 17 November rebuilt
candidate contains all four. The owner has already applied patch 4's equivalent
guarded helper to Ubuntu. Do not apply these changes twice. Patch 4 follows
patches 1–3; alternatively use the [guarded helper](../tools/README.md), not both.
For a matching earlier source
copy, preserve local work and check the next applicable patch before applying
it, from that source root:

```sh
git apply --check /path/to/the-next.patch
git apply /path/to/the-next.patch
```

Rebuild only the RHMI target and check the resulting imports and relocations.
Other upstream revisions may need adapted contexts. See the
[current checkpoint](../docs/2026-11-17-checkpoint.md) for validation and open
issues. These changes do not establish live CDS availability or an RPM UI.
