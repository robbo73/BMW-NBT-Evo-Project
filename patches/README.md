# Changes to the modified milestone-7 source

These patches preserve the two changes used for the 15 November 2026 native
RPM logging candidate. Apply them to the corresponding modified
`~/milestone-7` source, not to this documentation-only checkout.

1. `0001-b58-libstdcxx-compat.patch`: use the scanner-validated character range
   to construct a numeric token without the newer formatted range-error helper.
2. `0002-b58-validated-rpm-log.patch`: read and log accepted RPM, returning
   before reading when the incoming sample is rejected.

The supplied original source identifies NBT-AAD / nanaisu and
[Supra-iDrive6-Android-Auto](https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
and carries `SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0` and its
required copyright notice. These patches leave those source notices intact.
The complete upstream/modified application is not included here.

The current candidate already contains these changes; do not apply them twice.
For a matching earlier source copy, preserve local work and check applicability
before applying, from that source root:

```sh
git apply --check /path/to/0001-b58-libstdcxx-compat.patch
git apply --check /path/to/0002-b58-validated-rpm-log.patch
```

Then apply the patches with `git apply`, rebuild only the RHMI target, and check
the resulting imports. Other upstream revisions may need adapted contexts.
See the [checkpoint](../docs/2026-11-15-checkpoint.md) for validation and open
vehicle checks. Neither patch establishes live CDS availability or an RPM UI.
