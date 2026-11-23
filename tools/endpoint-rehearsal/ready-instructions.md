# Reviewed endpoint rehearsal: Chromebook storage bundle

23 November 2026. This bundle freezes the QNX ARM executable after offline
ELF/import review. It is a C-only fixed-text endpoint experiment. It is not
a manifest server for the plugin, a loader or a completed recovery tool.
Nothing here automatically connects to or changes the BMW.

## Offline check

Save nbt-endpoint-ready.tar.gz in Chromebook Linux files -> bmw-idrive.
In the ordinary Chromebook Linux terminal (robbo73@penguin):

```sh
cd ~/bmw-idrive
tar -xzkf nbt-endpoint-ready.tar.gz
cd nbt-endpoint-ready
sha256sum -c SHA256SUMS
```

All checksum entries should say OK. Preserve an existing extracted folder
instead of overwriting it. These commands only extract and verify local
files. Do not execute the QNX ARM binary on Chromebook Linux or Ubuntu.
No further rebuild or project patch is needed for the reviewed executable.

Executable identity: 13681 bytes, SHA-256
3df7b9161c30d5195975c37b614d92f0bdbfc23792d88c74691e30e735d7a625.
BUILD-REVIEW.md and audit.json record its static inspection. The bundle
contains our C sources and no vendor SDK output or BMW library/payload.

## Later vehicle work, not performed yet

The next connection can verify an OMAP RAM transfer/read-back and help-only
startup before testing the endpoint itself. Specific commands will be
supplied then. No transfer, activation or execution script is included here.

Default/help registers nothing. Its only active option would register one
PID-specific read-only /dev name serving the fixed 23-byte text
`nbt-endpoint-rehearsal\n`, with a configured ten-second deadline. The code
accepts no arbitrary path and does not access Plugins, HMI, the staged check
or RPM. Its only dynamic dependency is libc.so.3; all 33 required function
imports are present in the captured car libc.

Actual QNX startup, read/stat/seek behavior, timer/dispatch operation and
lookup failure after detachment or forced death remain untested. Each must
be observed separately with this inert endpoint. The primitive's value to
a future manifest design depends on those results; it is not established
by the build. Actual plugin loading and HMI restarts remain paused.
