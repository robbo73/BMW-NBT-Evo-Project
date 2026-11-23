# Inert QNX endpoint prototype: offline build only

23 November 2026. This is a C-only resource-manager experiment serving
`nbt-endpoint-rehearsal\n` under a unique `/dev/nbt_endpoint_rehearsal.<pid>`
name for a configured ten-second lease. It contains no manifest, payload,
plugin discovery link, RPM request, HMI access or activation operation.
The next action is an **Ubuntu cross-build for inspection**, not execution
on the BMW.

The purpose is to test whether an endpoint served by an independent process
becomes unavailable after that process exits or dies. This is still a
hypothesis about actual QNX behavior. Passing declaration checks or
compilation does not verify endpoint lifetime or establish recovery.

## Ubuntu build

Save nbt-endpoint-prep.tar.gz in your Ubuntu home folder, then run in the
**Ubuntu terminal**:

```sh
cd ~
tar -xzkf nbt-endpoint-prep.tar.gz
cd nbt-endpoint-prep
sha256sum -c SHA256SUMS
bash build_review.sh
```

Run each command only if the preceding command succeeds. Enter the Ubuntu
sudo password if prompted. The script verifies sources, runs the portable
policy checks, cross-compiles with the existing qnx65-armv7-toolchain:4.9
image, and collects readelf/hashes into:

```text
/home/rob/nbt-endpoint-review.tar.gz
```

Upload that archive for offline ELF/import/startup review. Do not execute
the target program before that review. No BMW connection is needed. This
script never mounts milestone-7, rebuilds either plugin, runs the ARM output
or edits vehicle files. Existing build/archive paths are refused; preserve
partial output if a build stops and inspect its error instead of bypassing
the guards. No new compiler installation or pip package is required.

## SDK basis and validation performed

The owner-supplied SDK interface capture passed every content hash. It
contains GCC 4.9.4/QNX 6.5 declarations for resmgr/dispatch/iofunc. Callback
signatures, structures and macros were checked against that exact capture;
vendor declarations remain private and are not included in this package or
GitHub. The adapter passed a separate private 32-bit, syntax-only callback
type check against the captured declarations. This is not an ARM ABI test
or a QNX build, and no resulting binary was produced by that check.

Sixteen Linux tests compile only the portable endpoint policy. They check
whole/partial reads, reassembly, seek offsets, zero-length/EOF reads,
negative/maximum integers, null outputs, randomized boundary cases, and
write/create/truncate refusal using supplied platform masks. Those tests
do not exercise QNX dispatch, namespace registration, default SDK handlers,
IPC, detachment or process death. The host policy shared object is a local
test artifact and is not the QNX server executable.

## Proposed target behavior, not yet run

Default/help returns without registering a path. The sole active option
would be --serve, using a fixed PID-specific name after requiring lstat to
report ENOENT. There is no caller-selected path. The server registers one
regular read-only file, reports READY and uses the SDK dispatch timeout API
with a 100 ms interval around a CLOCK_MONOTONIC deadline. It also handles
HUP/INT/TERM and ignores SIGPIPE so a lost output consumer need not abandon
cleanup. Actual timing and blocking behavior require native testing.

Open refuses write/create/truncate, and write requests return EROFS.
Namespace/metadata mutations, mmap and custom message operations are
disabled. Ordinary stat, seek, descriptor control and handle lifetime use the SDK defaults;
the bounded read callback serves only the fixed 23-byte text. There is no
backing file, filesystem deletion, resource transformation or access to any
real app data. The process does not load BMW frameworks, fork, kill another
process or change firmware/startup/coding.

Normal cleanup calls resmgr_detach, dispatch_context_free and
dispatch_destroy, followed by normal C exit. A successful detach return
would still require independent observation that new lookups fail. Forced
death deliberately bypasses those callbacks; whether the kernel/path manager
then makes the endpoint unavailable is the main future test, not an existing
guarantee. No SIGKILL or disconnect behavior has been tested for this server.

If later considered for a real manifest, file-reader compatibility, resource
lifetimes, stale handles, failed/partial detachment and guard death must all
be assessed separately. This prototype implements none of that integration.
Library-load probes and HMI activation/restarts remain paused; live RPM is
still unverified.
