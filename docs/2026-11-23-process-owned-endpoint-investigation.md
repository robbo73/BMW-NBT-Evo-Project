# Process-owned endpoint investigation — 23 November 2026

## Additional inert vehicle observations

After the explicit SIGHUP pass, the owner started another rehearsal:

```text
READY pid=18583668 base=/ramdisk/mm/.nbt-lease-rehearsal.18583668 lease_ms=10000
```

The intended step was closing a separate test SSH session using the local
client escape before expiry, then inspecting from the original console.
The owner later reported that the other session/process had been stopped;
the precise stop method/timing and a disconnect transcript were not supplied.
The original-console inspection printed `ABSENT: test fixture` for that
exact PID-specific path. It also required the RAM mount and previously
verified rehearsal executable to exist. This verifies absence after the
stop, not which cleanup path ran or a successful actual-SSH-loss test.
Do not relabel it as such. Normal deadline and explicitly delivered SIGHUP
remain the two positively identified vehicle cleanup paths.

A read-only inspection of the native OMAP shell process then returned:

```text
OMAP shell PID: 23269491
total 1336
-rw-r--r--  1 root root 684032 Nov 23 07:53 as
ls: No such file or directory (/proc/23269491/cwd)
ls: No such file or directory (/proc/23269491/fd)
Inspection complete
```

Only `as` was observed. It is the process address-space interface, not an
ordinary payload file or a new firmware dump. No memory contents were read
by these listings. The proposed Linux-style cwd/fd pathname route is not
supported by this observation and must not be assumed on this target.

No plugin was exposed or loaded by these operations. No HMI restart was
requested. Explicit screen-stability confirmation is still absent from
the pasted result; do not infer it from the lack of an error message.

## Candidate QNX-native approach: not implemented

The captured original car libc exports the following relevant functions
(availability checked through its runtime dynamic symbol table):

| Function | ELF value |
| --- | --- |
| dispatch_create | 0x3086c |
| dispatch_context_alloc | 0x30724 |
| dispatch_block | 0x3047c |
| dispatch_handler | 0x30274 |
| dispatch_timeout | 0x30068 |
| dispatch_destroy | 0x30160 |
| resmgr_attach | 0x31e28 |
| resmgr_detach | 0x31bf8 |
| resmgr_msgwrite | 0x4c768 |
| iofunc_func_init | 0x343f8 |
| iofunc_attr_init | 0x33578 |
| iofunc_read_verify | 0x36bdc |
| iofunc_open_default | 0x36540 |
| iofunc_lseek_default | 0x35968 |

A candidate design is a process-served read-only manifest endpoint, with
payload/resources retained separately in RAM. The observed scanner calls
stat on candidate manifest entries and skips failures, so a genuinely
process-owned endpoint could be useful if it becomes unavailable after
guard death. This is a hypothesis to test with inert data, not evidence
that the QNX namespace has the desired lifetime or that HMI will accept
such a file. A persistent alias to a normal RAM directory alone does not
address the demonstrated guard-death limitation.

Exact SDK types/callbacks, path ownership/detachment, reader/stat/seek
behavior, resource-path lifetime and every failure transition still need
review. Official QNX reference pages could not be retrieved in this cloud
session (HTTP tunnel 403); no claims here are based on reading those pages.
The next concrete input is the installed toolchain's own interfaces, not
another live-car probe or guessed modern/Linux headers.

## Prepared Ubuntu-only interface capture

[Capture script and instructions](../tools/resource-api-capture/README.md)
use the owner's existing QNX ARM GCC image to preprocess an include-only
C file. Output contains the SDK declarations/macros and compiler version
for private inspection. It creates no target executable, mounts no source
project, executes no vehicle code and needs no car connection. Shell syntax
and packaged checksums were checked in the cloud; the actual SDK capture
must run on Ubuntu, where the image is available. Vendor output is not
committed to GitHub.

After interface review, any prototype must be isolated from real Plugins,
serve dummy data only, and test ordinary expiry, handled signals and forced
death before a real manifest endpoint is considered. This preserves the
pause on plugin loading/HMI restarts. Live RPM remains unverified.

Follow-up: the owner supplied the SDK preprocessing output. Its verified
interfaces were used to prepare an isolated, fixed-text endpoint prototype
for an Ubuntu-only cross-build. See the
[interface review and preparation](2026-11-23-resource-api-review-and-endpoint-preparation.md).
No endpoint has been run on the vehicle and lifetime remains unverified.
