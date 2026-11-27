# Runtime-binding observer: Ubuntu results — 27 November 2026

The owner's uploaded offline review agrees with the frozen preparation:
all 22 source pins match, all 16 observer and 89 existing cache-reader tests
report success with no skips, and the synthetic observation is byte-identical
to the frozen cloud run. No native build or additional source change is needed
for this preparation. Actual vehicle bindings and the new observation mode
remain unverified.

## Uploaded evidence

Archive `nbt-runtime-binding-host.Pyki63.tar.gz`, 5004 bytes, SHA-256:

```text
db85358d61d9e5e382f9ff67eb8672dd38762f3338d7edb3091412e9a92e4d57
```

The hash matches the owner's pasted output. The archive contains exactly one
directory and six ordinary text/JSON files. Offline review checks all member
names, sizes, internal hashes and the original source manifest. The latter
matches the root manifest of the frozen
`nbt-runtime-binding-reader-prep.tar.gz` exactly, and all 22 pinned preparation
files also rehash correctly. The source pins describe that preparation tree,
not the current repository root README.

The [evidence directory](evidence/2026-11-27-runtime-binding-ubuntu/) preserves
the six uploaded files byte-for-byte, plus [audit metadata](evidence/2026-11-27-runtime-binding-ubuntu/audit.json)
and a separate whole-review hash manifest. The owner's original SHA256SUMS
is preserved without adding entries or rewriting its bytes.

| Item | Owner result |
| --- | --- |
| Python | 3.8.10 |
| Observer tests | 16 passed, 0.007 s, no skips |
| Existing cache-reader tests | 89 passed, 0.073 s, no skips |
| Synthetic binding slots | 27 |
| Synthetic stream-storage first words | 7 |
| Synthetic reads / aligned bytes | 78 / 808 |
| Synthetic JSON | 23832 bytes, exact cloud match |

Synthetic JSON SHA-256:

```text
a4a5277066b89d013b5c43c9ea84fa3a4087ddbb6613d9a8d3b16fb57c5417e9
```

The host logs report the VM's test execution; this review verifies their
contents, source pins and resulting output, rather than independently watching
the VM execute. The fake-memory result explicitly marks itself synthetic and
records no BMW connection or QNX execution. Its address matches must never be
presented as measurements from the real HMI.

## Consequence and next step

The [prepared observer](2026-11-27-runtime-binding-observer-preparation.md)
needs no compiler, SDK, Docker or new head-unit executable. The same source-only
preparation archive can be copied to Chromebook Linux for a later observation;
no replacement binary or new frozen candidate is introduced.

A later vehicle session should first obtain a fresh HmiMain3D PID and collect
the default mappings-only report, which reads zero process-memory bytes.
Only the explicit binding mode reads the fingerprinted existing pointer
slots and stream first words. Preserve stopped reports instead of editing
fingerprints, forcing resolution or loading a missing runtime. There is no
reason to rerun the standalone dlopen probe for this task.

The new vehicle mode has not run, so this result establishes no actual HMI
bindings, constructor/cleanup order, ABI compatibility, safe plugin execution,
live CDS callback or live RPM. Plugin activation and library-loading tests
remain paused. The full milestone-7 source/binaries, toolchain and hidden
vehicle stages remain unchanged.
