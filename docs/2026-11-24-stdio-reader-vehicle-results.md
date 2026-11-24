# Dummy alias stdio-reader results — 24 November 2026

Source: owner-pasted Chromebook/BMW console output. No direct cloud SSH
connection to the car is used. The experiment stays outside every actual
plugin root and serves only the known 23-byte dummy text.

## Package verification and RAM read-backs

The owner verified the ready archive and every included file. The package
identity is 20969 bytes, SHA-256
`d3128a58814dae37ce26efe8af4ea34017cc86942989622d76b5476c435cb404`.
The supplied transfer output confirmed local pins, RAM_COPY_COMPLETE and
independent read-back hash checks for both executables:

| Executable | SHA-256 |
| --- | --- |
| nbt_endpoint_rehearsal (13876 bytes) | 83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f |
| nbt_stdio_reader (9306 bytes) | a90b4183ea980987ca58d5a0b61f4a5ee78602272c0fba9f922f4a86ecdb0e13 |

Each read-back used the local temporary path
`/home/robbo73/bmw-idrive/nbt-stdio-readback.diFkmK`; it was reused sequentially,
with the corresponding expected hash checked before proceeding. The output
included separate VERIFIED lines for both names. Fixed OMAP RAM paths are
`/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e` and
`/dev/shmem/nbt_stdio_reader_a90b4183ea98`.

## New reader help-only startup passed

```text
Usage: /dev/shmem/nbt_stdio_reader_a90b4183ea98 --read-alias SHELL_PID
Revision: stdio-reader-1; default/help performs no file reads.
Reads only the fixed dummy-discovery.txt RAM alias; no XML/plugin/HMI operation.
Reader help exit: 0
```

This confirms startup and normal C exit of the new reader before active
file access, separately from its prior static review.

## Native stdio alias rehearsal passed

After another package/script-pin verification, the owner ran the unchanged
runner via SSH/QNET stdin and supplied the complete result:

```text
READY pid=4321396 path=/dev/nbt_endpoint_rehearsal.4321396 bytes=23 lease_ms=10000
PASS: stdio-reader-1; bytes=23 items=1; seek-end/tell/rewind/read/close
Stdio reader exit: 0
DETACHED reason=deadline; endpoint server exiting
Endpoint server exit: 0
DANGLING: dummy alias remains a link; target unavailable
CLEANED: dummy alias and owned fixture directory
PASS: dummy alias stdio-reader rehearsal
```

The reviewed reader's success path requires the parent to be a directory,
the alias to be a symlink, its followed target to be a regular file of the
expected size, successful fopen("rb"), fseek(SEEK_END), ftell==23,
fseek(SEEK_SET), fread(buffer,23,1,stream)==1, every expected byte to match
and successful fclose. The separate runner then requires reader exit 0,
helper normal deadline exit 0, a remaining symlink with unavailable followed
target and checked-empty owned-fixture cleanup. All completed in this run.
No WATCHDOG fallback output appeared. Actual elapsed time was not
independently measured. PID 4321396 identifies the endpoint helper; the
fixture directory uses the unprinted OMAP shell PID.

This establishes the native successful stdio access pattern through this
dummy process-owned alias. The [manifest loader trace](2026-11-24-manifest-reader-review.md)
identified this pattern before XML parsing, so the earlier cat-only coverage
gap is now closed for the tested 23-byte endpoint. The new reader's default
five-second alarm was not forced to expire on the car; its timeout behavior
under a native stall remains unverified.

## Checkpoint and remaining integration

No further BMW command is needed for this checkpoint. Next work is offline
preparation/review of the proposed manifest endpoint and resource-lifetime
handling. The existing helper still serves dummy text, not XML. No native
XML parser, actual manifest, plugin scanner or HMI lifecycle is involved
in this successful result.

Actual manifest parsing/admission, other sizes and seek cases, already-open
handles across provider death, HMI identity/lifetime monitoring and fault
containment remain unverified. Endpoint unavailability does not unload code
already in HMI. The transcript does not independently establish screen
stability or full-unit power/restart behavior.

No real Plugins/PluginsCoded path, hidden candidate stage, firmware, coding
or startup configuration was modified by the runner. No BMW framework was
loaded and no HMI restart was requested. Actual plugin loading and HMI
activation/restart trials remain paused. Live B58 RPM remains unverified.
