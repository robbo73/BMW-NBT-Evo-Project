# Corrected endpoint rehearsal: timeout-fix-1 storage bundle

23 November 2026. This is the newly reviewed corrected QNX executable.
The initial 3df7b9161c30 build failed its idle-timeout loop and must not be
rerun. Use this distinct bundle/folder to avoid mixing the two versions.

## Chromebook offline verification

Save nbt-endpoint-timeout-fix-ready.tar.gz in Linux files -> bmw-idrive.
In the ordinary Chromebook Linux terminal (robbo73@penguin):

```sh
cd ~/bmw-idrive
tar -xzkf nbt-endpoint-timeout-fix-ready.tar.gz
cd nbt-endpoint-timeout-fix-ready
sha256sum -c SHA256SUMS
```

Every entry should say OK. If the folder already exists, preserve/check
it instead of overwriting. This only extracts/checks local files: no SSH,
target transfer or execution occurs. The QNX binary is not a Chromebook
Linux/Ubuntu executable. No further Ubuntu rebuild or project edit is needed.

Target binary: 13876 bytes, SHA-256
83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f.
The expected target help revision is timeout-fix-1. Its new RAM basename
will be nbt_endpoint_rehearsal_83c6e473829e; exact guarded copy/read-back
commands will be supplied at the next connection.

BUILD-REVIEW.md and audit.json record the compiled correction and static
runtime checks. No host-test stubs or vendor headers are included. All 33
required function imports still exist in the captured car libc; the only
dynamic dependency is libc.so.3. Runtime validation is still pending.

## Scope of the later native test

Default/help registers nothing. The sole active mode would serve the fixed
23-byte text under one PID-specific /dev name for a configured ten-second
lease. The corrected loop checks receive ID before dispatch, so an idle
timeout context is retried; real handler errors remain fatal. It does not
load or serve a plugin/manifest, access HMI/RPM or replace any runtime.

A future test must demonstrate actual metadata/read behavior and endpoint
unavailability after expiry and forced death separately. The prior failing
test proved none of those. Actual dashboard activation/HMI restarts remain
paused; neither the initialization-check payload nor full RPM build changes.
