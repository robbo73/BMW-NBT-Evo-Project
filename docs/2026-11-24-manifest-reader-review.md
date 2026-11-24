# Manifest reader review and separate stdio client — 24 November 2026

Both [dummy alias vehicle tests](2026-11-24-discovery-link-vehicle-results.md)
passed. The owner returned to Ubuntu for the next offline step.

## Concrete reader requirement

Static disassembly of the unchanged original HmiMain3D traces the manifest
loader to fopen("rb"), fseek to end, ftell, fseek to start, a single
fread(buffer, length, 1, stream), and fclose before XML parsing. The read
must return one complete item. This is more than the earlier cat test
established; seek/stdio behavior of the process-served endpoint remains
unverified on QNX.

The [trace](../tools/stdio-reader-rehearsal/READER-TRACE.md) records exact
call sites, the original HMI hash and the path-expansion observations.
{pluginDir} expands using the managed record's discovery directory. The
library loader first checks the expanded path, with a lib+stem+.so fallback
if it does not exist. An existing explicit absolute path may avoid that
fallback, but no transformed manifest has been tried in HMI.

## Prepared Ubuntu-only cross-build

The new [C-only reader](../tools/stdio-reader-rehearsal/README.md) accepts
only a shell PID and constructs the existing fixed dummy alias path. It
checks the parent/link/target type and exact 23-byte size, then performs the
observed stdio access pattern and verifies the exact dummy bytes. Unlike
the native loader, it checks both fseek return values and rejects unexpected
lengths. It does not parse XML, reproduce the native allocator or load any
framework. A five-second default SIGALRM bounds this disposable reader's
active operation; it signals no other process.

Twelve Linux tests pass, including six injected stdio failures, path/data
validation and a blocked reader terminated by its alarm. The tests compile
only a temporary host copy with a relocated root literal. Fault wrappers
are linked only into the second host test binary. They are not in the
QNX build command. These checks do not emulate QNX IPC, ARM ABI or HMI.

The build script has passed Bash syntax checking. The captured real libc
exports the planned functions, including signal/alarm, stat/lstat and all
five stdio calls. The actual new QNX executable, CRT imports and startup/
relocation behavior still require review after the owner builds it.
No QNX compiler was run in the cloud and no target executable is included
in this preparation archive.

| Prepared item | Size / SHA-256 |
| --- | --- |
| nbt-stdio-reader-prep.tar.gz | 8509 bytes; d526b193ae644436f6b7912f684664bdda1d5748867d0258fba71907057cfec8 |
| nbt_stdio_reader.c | add047a1b725722106f37e58be3c0f167ac474e1ba1f3cadbb94a5908a0be136 |

The archive contains only the six prepared source/test/document files and
SHA256SUMS under one root (plus its test_support directory). Each archived
file matches the original preparation file, and the packaged checksums
pass. It contains no BMW binary, SDK output, manifest or payload.

## Next owner action and scope

On Ubuntu, extract the pinned archive into its new directory and run
bash build_review.sh. It runs the host tests and uses the existing
qnx65-armv7-toolchain:4.9 Docker image for an isolated ARM C build, with only
this preparation directory mounted. It refuses an existing build output or
review archive. Upload /home/rob/nbt-stdio-reader-review.tar.gz for offline
ELF/import review. No new vehicle execution is requested at this stage.

The existing endpoint binary, alias script, milestone-7 source/full RPM
binary and hidden initialization-only payload are untouched. No BMW
connection is needed. This is not a completed manifest endpoint, HMI
lifetime guard or native initialization trial. Library-loading/HMI
activation/restart trials remain paused. Live B58 RPM is unverified.
