# Native RPM logging checkpoint — 15 November 2026

**Historical checkpoint.** The [17 November update](2026-11-17-checkpoint.md)
supersedes the candidate status and next vehicle steps below. Library-loading
tests and HMI activation are currently paused after observed unit restarts.

The objective is live B58 RPM on the BMW M140i's NBT Evo without Bluetooth or
ENET equipment during normal use. This checkpoint is an offline build and
static-analysis milestone. It does not establish vehicle loading or live RPM.

Later findings from the connected car, including host identification, actual
framework comparisons and writable storage, are recorded in the
[vehicle preflight](2026-11-15-vehicle-preflight.md). The outstanding list below
describes the state at this earlier offline checkpoint.

## Current source and tools

- Modified application source: `~/milestone-7` on the Ubuntu VM; native plugin
  source under `rhmiapp/`.
- Docker build context: `~/qnx65-armv7-toolchain`; installed image:
  `qnx65-armv7-toolchain:4.9`. Uploaded plugin compiler metadata is GCC 4.9.4.
- The Makefile builds the plugin with `qcc -Vgcc_ntoarmv7le_gpp`, ARMv7,
  softfp/VFPv3, PIC, C++11 and the App/Core framework libraries.
- The Dockerfile also supports GCC 8.5 and defaults to that base. Use the
  existing 4.9 image for the recorded build; a default Docker rebuild is not
  evidence of reproducing this compiler.
- Complete application source and the SDK/toolchain inputs are not in this
  repository. Uploaded archives were inspected in the cloud; builds and the
  repository host suite were run by the owner on Ubuntu.

## Source corrections

1. `b58_telemetry.hpp` used `std::string::substr()` to copy a number token.
   GCC 4.9.4 inlined a bounds check importing
   `_ZSt24__throw_out_of_range_fmtPKcz`, absent from the copied BMW runtime.
   The parser's scanner already establishes the token bounds. Constructing
   the token from its pointer and length removes that helper import.
2. `onB58RpmChanged()` now calls `b58::read()` after a successful update and
   logs `B58 RPM: validated %.1f rpm`. Rejected updates return before reading,
   avoiding presentation of an earlier reading as the rejected sample.

Both changes are preserved under [patches](../patches/README.md). Neither adds
an RPM screen. Disassembly confirms the final callback calls the bridge reader;
the log format is present in the uploaded binary.

## Exact candidate

`nbt-rpm-test-package.tar.gz` contains:

- `libNbtAad.so`
- `NbtAad.manifest`
- `NbtAad.xml`
- `NbtAad_ALL_Texts.zip`
- `NbtAad_ALL_Images.zip`

Archive SHA-256:

```text
1518475e81354d59c2d03e3998196dadf4bd67008e55e97f32b5e7f460f8f69f
```

The current plugin is 112119 bytes, SHA-256:

```text
09902c834a37f0fb92e075f5228d4442534df432d5f4c48c2d9c6f8137162679
```

See [candidate-SHA256SUMS](candidate-SHA256SUMS) for all five files. Keep the
archive and backups separately; the compiled plugin and BMW libraries are not
included in this documentation checkout.

## Completed checks

- Runtime copied over SSH from
  `/net/hu-omap/fs/sda0/lib/libstdc++.so.6`. Its `repository/istep/lib` path is
  a hard link to the same file. Both Chromebook copies were 849036 bytes with
  SHA-256 `57a95b3afd5df1d78e7f9fa9c96666501c540bfd04dd156a8dd14ae49d443f3c`;
  the Ubuntu/uploaded copy matches.
- The final plugin's 38 identified required C++ runtime imports all have
  matching visible named exports in that runtime. Its 23 required BMW framework
  imports match the supplied App/Core library copies. The logging change adds
  no undefined symbol names relative to the parser-fixed binary. No
  `out_of_range` import remains.
- All four packaging assets match the reviewed versions. The manifest selects
  the full `NbtAad.xml`; local references and checked main-UI source IDs match.
  Text/image ZIP CRCs pass, with required text IDs and image assets present.
  The Direct/Multimedia alternatives omit current application models/events
  and are not selected by the manifest.
- Original/proposed parser and bridge passed 557 host assertions, plus
  differential checks of 2000 deterministic mixed/malformed inputs and 500
  generated RPM payloads, with ASan/UBSan and identical output. These were
  separate inspection-harness checks, not vehicle or QNX execution.
- Ubuntu's repository check completed with:

  ```sh
  cd ~/milestone-7
  make -C tests HOST_CXX=g++-10 check
  ```

  The lifecycle ThreadSanitizer test passed, and the runner reported
  `[CHECK] all host tests passed`. Two checks remained skipped: the 32-bit
  protocol variant (no `-m32` toolchain) and schema test (`protoc` absent).
  Existing ordinary test binaries may have been reused; this was not a clean
  rebuild of every test with GCC 10.

Ubuntu 20.04's installed GCC 9 could not find `libtsan_preinit.o`; reinstalling
its development package did not fix it. GCC 10 supplies the file. The test
Makefile uses **`HOST_CXX`**, not `CXX`. This host compiler selection does not
change the QNX Docker image. OpenSSL deprecation warnings were nonfatal.

## Rebuild the native plugin

From Ubuntu, after preserving source and the previous binary:

```sh
cd ~/milestone-7
sudo docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$HOME/milestone-7:/src" \
  -w /src \
  qnx65-armv7-toolchain:4.9 \
  make -B rhmiapp
```

Re-audit any newly built binary before deployment. Building with this command
does not prove vehicle compatibility or reproduce the exact candidate hash.

## Outstanding vehicle investigation

1. Locate the actual RHMI host across the relevant Qnet nodes and inspect its
   mapped libraries. `HmiMain3D` is a source-derived candidate, not a confirmed
   process on this vehicle. Rediscover PIDs after power cycles.
2. Match the car's loaded App/Core/C++ libraries to the reviewed copies. Check
   C/POSIX/socket providers and runtime search order as needed. The plugin
   still has no RPATH/RUNPATH and retains DT_TEXTREL. The manifest's base-name
   library lookup and native UI placement have not been exercised here.
3. Establish a reversible deployment/recovery procedure, then test loading.
4. Observe genuine `engine.RPMSpeed` payloads, validate their schema, scaling,
   freshness and update rate, and compare changing RPM with the instrument
   cluster during a stationary test. A lone zero value is insufficient.
5. Add an RPM screen only after the native feed works, then test startup and
   operation after a head-unit restart with external adapters disconnected.

`NbtEvoJacintoDiagHUHighApp` owns TCP 6801/6811 and has the Ethernet diagnostic
mapping. It is **not** a confirmed RHMI plugin host. Previously observed PIDs
are historical observations, not fixed identifiers.

The candidate has not been reported installed. Identify the host through
existing native plugins/framework mappings rather than assuming our plugin
already appears in process mappings. No firmware dump has been taken.

## Separate diagnostics and access findings

- External HSFZ identification/VIN requests to NBT address `0x63` worked.
  The DME-address `0x12` attempt did not establish a successful DME response.
  Do not treat head-unit VIN retrieval as proof of DME communication.
- Reference ISTA dynamic-DID requests are not yet validated for this B58.
  Clear/define dynamic DID operations are not read-only measurement requests.
- Bavarian activation is needed again after the car shuts down/sleeps; it can
  be closed while SSH access continues. The mechanism remains unknown. One
  socket snapshot showed inetd owning the SSH listener and sshd handling the
  accepted connection.
- The head-unit shell has no demonstrated Python or SSH client. Use the
  Chromebook's Linux terminal for SSH/copying. Its per-connection
  `-oHostKeyAlgorithms=+ssh-rsa` option enabled negotiation with the older
  server; host-key verification remains enabled.
- `slogspy` is available on QNX 6.5. Its `-t` is a read wake-up timeout, not a
  guaranteed total capture duration. Avoid its history-erasing `-e` option.

Even Realities G2 integration remains deferred until native RPM works.
