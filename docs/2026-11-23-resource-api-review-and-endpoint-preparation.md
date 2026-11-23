# SDK interface review and inert endpoint preparation — 23 November 2026

## Capture identity and scope

The uploaded nbt-qnx-resource-api-review.tar.gz is 37361 bytes, SHA-256
afa952101d28346df4092b56c3c5cd099367660ee2c48afb9c85d69f8cd36111,
matching the owner's output. Its exact five regular-file members and all
recorded hashes passed. The include-only input matches the supplied source.

| Member | Bytes | SHA-256 |
| --- | ---: | --- |
| resource_api.c | 266 | be919745c617de89243f6dab3e6de1e3ac8f16226a67dd462842b4eec0d89afc |
| resource_api.i | 92082 | 4cf95bd71aa96177d49986e18ba05faa6e1b4b4aaa82cde50de839943f4eac51 |
| resource_api.macros.txt | 68535 | 86096ca40f568882a56445276a5057a224bda5ccf2f390b85f33ce64e8f838fb |
| compiler-version.txt | 247 | 3880a9760aca57eb5e4d6664429d39e190ffb63f159578cddd5f2fe33b517b55 |

Compiler version is arm-unknown-nto-qnx6.5.0eabi-gcc 4.9.4. The declarations
are from the installed SDK, not modern/Linux substitutes. Vendor output is
retained privately outside Git; only hashes and our own code/notes are
committed. No vehicle connection/execution or target binary was part of
this capture.

## Relevant interfaces and corroboration

The capture supplies resmgr_context_t, resmgr/iofunc callback tables,
iofunc_attr_t/ocb_t, io_open_t/read_t and the dispatch API. Required callback
signatures and flag fields are now inspectable. For example, dispatch_timeout
takes dispatch_t plus a relative timespec; read uses an OCB with signed
64-bit offset and a message with signed 32-bit request length.

Offline disassembly of the captured car libc's dispatch_timeout at 0x30068
shows it storing two timeout words and setting a dispatch-state flag. This
corroborates using the declared API but does not prove scheduling bounds or
every block/timeout/error transition. The namespace lifetime and HMI reader
behavior are not derivable from these declarations alone.

## Prepared code and checks

[The inert endpoint prototype](../tools/endpoint-rehearsal/README.md) serves
one fixed text string at a unique PID-specific /dev path. It has no manifest,
payload, plugin link, HMI operation or arbitrary endpoint path. Its intended
lease is ten seconds with a monotonic check and a 100 ms dispatch timeout.
It refuses writes and disables unsupported mutating/control callbacks.
Help/default registers nothing. Normal shutdown uses SDK detachment and
normal C cleanup; forced-death behavior is deliberately left for testing.

Sixteen portable Linux policy checks pass, including bounded/partial reads,
EOF/seek/negative/extreme inputs, 4000 deterministic randomized cases and
write-open refusal. The actual QNX adapter also passed a private syntax-only
callback type check against the captured declarations using 32-bit parsing.
That check avoids mixing host wchar_t/SDK definitions, produces no target
output and proves neither ARM layout nor kernel behavior. Those limits are
explicit; no QNX server/IPC simulation is being claimed.

The next user action is an Ubuntu cross-build using the existing QNX Docker
image. The source-only preparation package verifies checksums, reruns the
portable policy checks and writes a separate nbt-endpoint-review.tar.gz with
the target executable, sources, build log and ELF reports. It does not mount
or modify milestone-7, use either plugin payload, execute ARM code, or
contact the car. Actual ELF dependencies/imports/startup must be reviewed
before any native test.

The proposed process-owned manifest approach remains hypothetical. Native
expiry, signal/forced death, endpoint lookup/read/seek/error semantics and
reader/resource lifetime must be demonstrated with inert data first. No
change to the pause on library loading or HMI activation is made here.
See the [endpoint investigation](2026-11-23-process-owned-endpoint-investigation.md).
