# Dummy discovery-link results — 24 November 2026

## Ubuntu verification passed

The owner supplied a successful archive checksum, all six packaged payload
checksums and all 13 Linux fixture test results. The run completed in
2.362 seconds and ended with:

```text
OK
OFFLINE CHECKS PASSED: no ARM execution or BMW connection performed
```

The unchanged 13072-byte archive has SHA-256
`98158650111b5679997da7293a4c6155530a173f066b9c38de3251d792e6b87d`.
The [preparation record](2026-11-24-discovery-link-preparation.md) identifies
the exact shell script and reused endpoint executable. No new QNX build or
milestone-7 edit was needed.

## Native normal-deadline alias test passed

The owner reported ignition on, engine off and an active BMW SSH connection.
The supplied Chromebook output confirms all package checksums and the two
independent script/binary pins passed. RAM_COPY_COMPLETE was followed by:

```text
/home/robbo73/bmw-idrive/nbt-alias-readback.U7XkED: OK
```

The SSH/QNET stdin help invocation then returned the expected usage. A
password retry occurred on the next SSH invocation; authentication then
succeeded and the --deadline trial completed with this exact output:

```text
READY pid=6787188 path=/dev/nbt_endpoint_rehearsal.6787188 bytes=23 lease_ms=10000
ALIAS_READ: nbt-endpoint-rehearsal
DETACHED reason=deadline; endpoint server exiting
Endpoint server exit: 0
DANGLING: dummy alias remains a link; target unavailable
CLEANED: dummy alias and owned fixture directory
PASS: --deadline dummy discovery-link rehearsal
```

This establishes successful followed alias lookup as an ordinary file,
reading the expected text through the alias, normal helper exit 0, an
alias that remains a symlink while its target is unavailable, and removal
of the alias and its owned checked-empty fixture directory. Actual elapsed
time was not independently measured. No WATCHDOG fallback output appeared.
The fixture directory uses the OMAP shell PID, which was not printed;
6787188 identifies the endpoint helper only.

The script creates only
`/ramdisk/mm/.nbt-endpoint-alias.<shell-pid>/dummy-discovery.txt`, outside
all real plugin roots. It uses no .manifest filename, parser, scanner,
BMW framework, plugin, CDS request or HMI operation. No HMI restart was
requested. Screen stability is not independently established by stdout.

## Next bounded check

The same script's --forced-death branch is prepared but its alias case
has not yet run on the BMW. It starts a new helper, first reads through a
new dummy alias, kills only that child, requires wait status 137, and checks
that the alias becomes dangling before cleaning up. The endpoint-only
forced-death result is already [verified separately](2026-11-24-endpoint-forced-death-results.md).

These isolated results do not establish manifest-reader compatibility,
real scanner admission, already-open handle behavior, resource lifetime,
fault containment or stable native C++ initialization. The initialization-
only payload remains hidden; library-loading and HMI activation/restart
trials remain paused. Live B58 RPM remains unverified.
