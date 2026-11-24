# Separate stdio reader: rebuilt ELF review — 24 November 2026

The owner supplied the QNX cross-build after 12 passing Ubuntu tests
(5.209 seconds). Its original six source/test/document payloads match the
prepared files exactly. The 15323-byte uploaded archive has SHA-256
5220e2301802ae896221daaed17de07b5e0ebe9c590f80d2834c2d62c307be59,
matching the owner's report. Its 16 members are the expected ordinary
files and build output directory, with no links/traversal/extra members.
All embedded preparation checksums pass.

## Actual executable

| Field | Reviewed value |
| --- | --- |
| Size | 9306 bytes |
| SHA-256 | a90b4183ea980987ca58d5a0b61f4a5ee78602272c0fba9f922f4a86ecdb0e13 |
| Type/architecture | ELF32 little-endian ARM, ET_EXEC, flags 0x5000002 |
| Entry | 0x100834 |
| Interpreter | /usr/lib/ldqnx.so.2 |
| DT_NEEDED | libc.so.3 only |
| Required function imports | 22, all exported by the captured car libc |
| Relocations | 24 R_ARM_JUMP_SLOT; two R_ARM_COPY |
| COPY objects | errno: 4 bytes; _Stderr: 80 bytes; both match actual libc sizes |
| Init/fini arrays | frame_dummy 0x1009f0; __do_global_dtors_aux 0x1009ac |

There is no TEXTREL, RPATH/RUNPATH, unsupported relocation, test wrapper or
C++ stream initialization. The two frame-info imports are optional weak
CRT hooks. These are static ELF findings, not proof of native startup or
compatibility of every runtime operation. See the
[audit metadata](../tools/stdio-reader-rehearsal/audit-2026-11-24.json).
The actual captured libc hash is recorded there.

## Compiled behavior checked

Main is 1016 bytes at 0x100a4c. Default/help and bad-argument returns precede
all path/IO operations. The decimal PID bounds check and the fixed RAM alias
path are present. No arbitrary path or PID to signal can be supplied.

The default SIGALRM setup is at 0x100bb0 and alarm(5) at 0x100bc0. The
parent and alias lstat checks are at 0x100bcc/0x100c30, followed stat at
0x100c74, with the expected directory/link/regular-file and size checks.
The actual executable then calls fopen at 0x100cc8, fseek(SEEK_END) at
0x100cdc, ftell at 0x100d2c and requires 23, fseek(SEEK_SET) at 0x100d78,
fread(buffer,23,1,stream) at 0x100da4 and requires one item, memcmp at
0x100de0 and fclose at 0x100e10. The successful fclose return supplies
zero to alarm at 0x100e1c, then the PASS marker is printed.

The binary contains the expected fixed dummy path/body and no host fault
selector. It signals only itself through the bounded alarm, writes no
file, and loads no BMW library. It contains no XML parser, manifest or
HMI operation. The five-second alarm's actual target behavior remains
untested, along with the new reader's startup/stdio operations.

## Ready bundle and runner

The new [runner](../tools/stdio-reader-rehearsal/check_stdio_alias.sh)
reuses the tested dummy-link deadline/cleanup pattern and invokes this
reader in place of cat. It checks both fixed RAM executables before any
fixture creation. It requires reader exit 0, helper normal exit 0, the
remaining alias's followed target to be unavailable, and checked-empty
fixture cleanup. Its fifteen-second fallback and cleanup signal only the
new endpoint helper child, never a pre-existing process.

Nine new Linux runner checks pass (1.874 seconds), including the actual C
reader source compiled for the host, failure propagation, default/bad args,
missing/linked reader, missing endpoint, overrun, unexpected hidden-entry
preservation and hangup cleanup. They use ordinary files and shorter sleeps,
not a QNX namespace/ABI or HMI model. The owner's original 12 tests passed
against the identical supplied source; no new C build is needed.

The private ready archive nbt-stdio-reader-ready.tar.gz is 20969 bytes,
SHA-256 d3128a58814dae37ce26efe8af4ea34017cc86942989622d76b5476c435cb404.
It includes the exact reviewed reader, the unchanged 13876-byte previously
tested endpoint, runner, own source/tests, trace, audit metadata and pins.
Every archived file matches its embedded checksum. No BMW binary, SDK
output, real manifest or plugin payload is included. The bundle's binaries
remain outside GitHub. See the
[storage and next-test instructions](../tools/stdio-reader-rehearsal/ready-instructions.md).

## Next step and limits

Store and verify the ready bundle on the Chromebook. The next isolated
vehicle sequence requires separate RAM read-back hashes, reader help-only
startup/normal exit, then the dummy alias stdio test. The supplied build
review archive is an input to this inspection, not the next target package.
No ARM executable was run in the cloud, no BMW connection was made, and
no new vehicle execution is claimed by this review.

No source/binary/manifest in milestone-7 or either hidden trial stage was
edited. The endpoint/alias vehicle results remain distinct from this new
reader. Native manifest parsing/admission, resource lifetime, HMI-fault
containment and C++ initialization remain unverified. Actual plugin
loading and HMI activation/restart trials remain paused. Live RPM has
not been demonstrated.


## Vehicle follow-up

The owner subsequently verified the ready bundle and both RAM read-backs,
passed new-reader help-only startup with exit 0, then passed the isolated
stdio alias test: exact bytes and all seek/read/close checks, both exits 0,
dangling alias and owned-fixture cleanup. See the
[complete vehicle result](2026-11-24-stdio-reader-vehicle-results.md).
This does not establish native XML parsing, HMI integration or live RPM.
The original static audit and frozen package hashes are unchanged.
