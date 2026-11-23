# Inert endpoint: QNX build review — 23 November 2026

The owner supplied the Ubuntu cross-build archive. The source identities,
ELF/runtime imports and relevant callback layout checks below pass offline.
The ARM executable has not been executed in the cloud or on the vehicle.
Endpoint registration, reading and lifetime are still unverified.

## Frozen identities

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| nbt-endpoint-review.tar.gz | 16848 | 79f490438cc0893df4b651d6ee04fe2b5d761bc816ab16c1fe787f052e284b6c |
| nbt_endpoint_rehearsal.c | 6222 | 33ffb438dd7f6efed28bb78b9ee7e0561cde4f7b3a89b93a8c19aee4ec0367a6 |
| endpoint_policy.c | 953 | 4536d4f66b5e6786b9ea89075b3911bad983dc453f22489a19680ed13c157578 |
| endpoint_policy.h | 434 | 4e4d168df3ac9433598964568a4c6b89288d6aab6784300b34f92b85765ca9bf |
| QNX nbt_endpoint_rehearsal | 13681 | 3df7b9161c30d5195975c37b614d92f0bdbfc23792d88c74691e30e735d7a625 |

All seven preparation files, including the build/test scripts and checksum
list, match the supplied package byte-for-byte. The exact archive member
set contains regular files and one build directory; no extra paths or links
were accepted during extraction. The owner's host log records all 16 policy
checks passing in 0.081 seconds. Those remain policy checks, not tests of
QNX IPC, dispatch or namespace behavior.

## ELF and runtime

- ELF32 little-endian ARM ET_EXEC, flags 0x5000002, entry 0x100b0c.
  Interpreter: /usr/lib/ldqnx.so.2. The header's generic System V field is
  not sufficient by itself to establish QNX compatibility.
- DT_NEEDED contains only libc.so.3. There are no RPATH, RUNPATH or TEXTREL
  tags, BMW framework/C++ runtime dependencies or R_ARM_REL32 relocations.
- All **33 required undefined function symbols** are exported by the
  captured car libc, SHA-256
  7d1199d75bd1187dc3e1842fa89320e9eb82d7215ccf4ce251edcf033cf46baf.
  Its stripped image was read through PT_DYNAMIC without modifying it.
- The R_ARM_COPY objects match that provider's sizes: _Stdout 80 bytes,
  _Stderr 80 bytes and errno 4 bytes. The remaining 35 dynamic relocations
  are R_ARM_JUMP_SLOT, including the two optional weak frame-info imports.
- Init-array: frame_dummy at 0x100cc8. Fini-array:
  __do_global_dtors_aux at 0x100c84. Normal C startup/exit and ordinary
  resmgr/dispatch cleanup remain; there are no C++ stream constructors or
  cleanup bypasses.

The imports include the expected resmgr_attach/detach, dispatch functions
and iofunc defaults. There is no dlopen/dlsym, socket, fork, process-killing,
filesystem-deletion or backing-file-open import. The only served bytes are
the fixed 23-byte `nbt-endpoint-rehearsal\n` string.

## Compiled implementation checks

Main at 0x100ea8 is 1424 bytes. Its default/help branch returns before any
endpoint setup. --serve uses the fixed PID-specific
/dev/nbt_endpoint_rehearsal.%ld name after the absent-path check; no caller
path is accepted. No manifest, plugin-discovery link or HMI call exists.

Relevant SDK usage was checked against the original car libc disassembly:

- The compiled callback initializer requests 8 connect and 26 I/O functions,
  matching the car iofunc_func_init limits.
- iofunc_attr_init clears 0x58 (88) bytes. The caller's allocated attribute
  area covers this, and its nbytes assignment is at attribute+0x28. The
  provider's mode field is at +0x4c, matching the captured SDK declarations.
- The read callback uses OCB offset +0x08, status at context+0x48 and IOV
  data/length at +0x54/+0x58. The context/provider fields reviewed are
  consistent with the captured SDK. This is not an exhaustive ABI proof.
- The compiled open policy rejects write bit 0x2 and create/truncate mask
  0x300 with EROFS (30); its write callback also returns EROFS. Read checks
  the SDK verifier, requires the supported transfer type, and bounds signed
  lengths/offsets before forming the static-data reply.
- Dispatch timeout receives a relative 100000000 ns timespec; the deadline
  is based on CLOCK_MONOTONIC. Normal shutdown calls resmgr_detach with
  _RESMGR_DETACH_ALL, then frees context and destroys dispatch. The captured
  context-free/destroy paths were inspected alongside this call order;
  runtime finalization remains unverified.

Callback bounds, namespace ownership, actual timer/block behavior, client
read/seek/control compatibility and detachment after requests remain native
test questions. Compilation and symbol availability do not answer them.
The currently running unit's firmware/runtime identity is not reverified
by this offline inspection.

## Next isolated step

A separately supplied nbt-endpoint-ready.tar.gz freezes this exact binary,
its own sources and the review metadata/checksums. It contains no vendor
headers, car libraries, manifest or plugin payload. No binary is committed
to Git. No additional Ubuntu rebuild is needed for these reviewed bytes.

Ready archive: 13126 bytes, SHA-256
b527ceac3f38bdaddefd6e9c9e433d8ed183f603fc5f0219c17303111421389e.
The extracted checksum list and exact embedded target bytes were verified
without executing the program. The
[ready instructions](../tools/endpoint-rehearsal/ready-instructions.md)
only extract/check local files. Static metadata is preserved as
[audit-2026-11-23.json](../tools/endpoint-rehearsal/audit-2026-11-23.json).

At a later BMW connection, a guarded RAM transfer/read-back and help-only
startup check should precede a bounded inert endpoint test. Reading the
fixed text and observing lookup failure after expiry, signal and forced
death are distinct outcomes to record. Do not label successful attachment
or a return code as proof of endpoint disappearance. No vehicle commands
or execution were performed as part of this review.

This does not yet implement a process-owned manifest or solve real-plugin
recovery. Reader/resource lifetimes and partial-failure behavior need their
own design if this primitive works. Actual plugin loading and HMI restart
trials remain paused; native initialization and live RPM are unverified.
