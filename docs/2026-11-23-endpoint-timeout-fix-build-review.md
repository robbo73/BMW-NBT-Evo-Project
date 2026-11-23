# Endpoint timeout-fix-1: QNX build review — 23 November 2026

The owner built the corrected source on Ubuntu and supplied its review
archive. Source identity, compiled receive-loop correction and runtime
import checks pass offline. The corrected ARM executable has not been
run in the cloud or on the vehicle. No endpoint serving/lifetime pass is
claimed from this review.

## Verified identities

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| nbt-endpoint-timeout-fix-review.tar.gz | 20943 | 40732d41cc71d605d002249082c563a0dec228efdf7e42ad1783b18016314148 |
| nbt_endpoint_rehearsal.c | 6787 | 72b7347d136c3b0b6ceec5fc6ab332858e4d828ad241f5809d247a42072a2464 |
| endpoint_policy.c | 1414 | a007d08a5196351e1da51eda3233fbc2ed26d20df81e89bf0c1720808bf2cb57 |
| endpoint_policy.h | 696 | 305b802f0f97309cebdcfd849bd240ff94a61a12fd29f0a09d5f5758594a7b64 |
| QNX nbt_endpoint_rehearsal | 13876 | 83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f |

The archive matches the owner's fingerprint. Its exact expected regular
files and two directories were accepted, with no links/extra members.
All ten preparation files match the correction package byte-for-byte.
The supplied host log records all 25 checks passing in 0.146 seconds:
16 portable policy checks and nine main-loop contract checks. The latter
use deliberate host stubs, not QNX headers, an ABI model or kernel IPC.

## Compiled correction

Main is at 0x100ee4, size 1416 bytes. Its receive loop:

- Clears errno at 0x101320 and calls dispatch_block at 0x101324.
- Captures errno immediately at 0x101328 and retains a returned context.
  A non-null context's first signed receive-ID word is loaded at 0x101340;
  a null result supplies -1 instead.
- Calls nbt_endpoint_dispatch_action at 0x10134c. Retry branches back to
  the stop/deadline checks at 0x101360, without invoking a handler.
- Clears errno at 0x10136c before dispatch_handler at 0x101370. Handler
  failures remain fatal; an empty error is replaced by EIO for reporting.

The action routine at 0x101520 is 48 bytes. A valid context and nonnegative
receive ID return MESSAGE, including pulses and messages with stale errno.
Otherwise it retries only EINTR (4) or the target ETIMEDOUT (0x104/260).
The compiler implements this exact pair by clearing bit 0x100 and comparing
with 4; other errors return FAIL. It does not blindly ignore handler errors.

This matches the actual car libc receive behavior identified in the
[failure analysis](2026-11-23-endpoint-timeout-correction.md), where timeout
can return the existing context with receive ID -1. It establishes that
the reviewed fix is in these compiled bytes, not that all endpoint behavior
will work on the unit.

## Runtime and host-stub exclusion

- ELF32 little-endian ARM ET_EXEC, flags 0x5000002, entry 0x100b0c;
  interpreter /usr/lib/ldqnx.so.2; only DT_NEEDED is libc.so.3.
- All 33 required undefined function names are unchanged from the initial
  build and are exported by the captured libc (SHA-256
  7d1199d75bd1187dc3e1842fa89320e9eb82d7215ccf4ce251edcf033cf46baf).
  There are no newly required imports.
- The three R_ARM_COPY objects match their provider sizes: _Stdout 80,
  _Stderr 80 and errno 4 bytes. The other 35 dynamic relocations are
  R_ARM_JUMP_SLOT. No R_ARM_REL32, RPATH, RUNPATH or TEXTREL is present.
- Normal C init/fini arrays remain frame_dummy (0x100cc8) and
  __do_global_dtors_aux (0x100c84), with optional weak frame-info imports.
  There are no BMW/C++ dependencies or cleanup bypasses.
- The revision string `Revision: timeout-fix-1`, fixed dummy text and
  PID-specific endpoint-name pattern are present. MOCK_LOOP,
  NBT_TEST_SCENARIO, __wrap_lstat, __wrap_clock_gettime and fake_qnx markers
  are absent. The native binary uses the real SDK calls, not the host stubs.

The callbacks and resource-manager configuration retain the previously
reviewed read-only data behavior, types and normal cleanup. No plugin,
manifest, resource transformation, HMI process control or RPM operation
has been added. Static matching is not an exhaustive ABI/runtime proof.

## Frozen corrected bundle and next step

The separately supplied nbt-endpoint-timeout-fix-ready.tar.gz contains this
exact executable, our matching C sources, metadata/review and SHA256SUMS.
It contains no test stubs, vendor SDK output, BMW libraries or plugin data.
No binary is committed to Git. No further Ubuntu rebuild is needed for
these reviewed bytes.

Corrected ready archive: 13383 bytes, SHA-256
ca08383dd3fdd20aae73eae450c0876fc8359a3dc13678c6dc33ee6311954322.
Its extracted checksum list and exact embedded executable were verified
without running ARM code. See the
[storage instructions](../tools/endpoint-rehearsal/timeout-fix-ready-instructions.md)
and [static audit metadata](../tools/endpoint-rehearsal/audit-timeout-fix-2026-11-23.json).

The old 3df7b9161c30 executable/bundle remain historical evidence and must
not be rerun. A future transfer must use a new RAM filename ending
83c6e473829e and verify the full hash before execution. Default/help should
identify timeout-fix-1. The next isolated native test is still metadata,
fixed-text reading and deadline cleanup, with a helper-only fallback.
Registration alone or static checks do not prove those outcomes.

The corrected build has not yet registered an endpoint, served a client,
reached native expiry or demonstrated lookup failure after forced death.
Actual plugin activation/HMI restart trials remain paused. The original
initialization-check/full RPM builds are unchanged; live RPM is unverified.
