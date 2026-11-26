# Held-descriptor reader: QNX build review — 26 November 2026

The owner uploaded nbt-open-handle-reader-review.tar.gz after building on
Ubuntu. All 22 host checks passed in 6.443 seconds. The archive is 33572
bytes, SHA-256
`842c9bc59b7b1d8398ef9c2c6747858ba83a8ee0739cc5b294b9efe9bbe01368`.
Its exact 24-member set contains only ordinary files and one directory.
All ten preparation files match their hashes and the repository snapshot;
the checksum file and seven recorded build hashes were also checked.

This is static inspection, not a QNX run. The earlier native 586-byte
endpoint/stdio result is separate. No actual controller or car command
is included in this reader review.

## Executable identity and runtime

| Field | Result |
| --- | --- |
| File | nbt_hold_reader_586 |
| Size | 22345 bytes |
| SHA-256 | 9a54c7f4dba539d25861f6e98a018d778bec62eb86462b7b208138a4be34de79 |
| ELF | ELF32, little-endian ARM, ET_EXEC, flags 0x5000002 |
| Entry | 0x100a2c |
| Interpreter | /usr/lib/ldqnx.so.2 |
| Needed library | libc.so.3 only |
| Required dynamic function imports | 32; all exported by the captured car libc |
| Relocations | 34 R_ARM_JUMP_SLOT and one R_ARM_COPY |
| COPY object | errno, four bytes; matches the provider |

The only dynamic weak imports are the ordinary register/deregister frame-info
hooks. Init/fini arrays contain frame_dummy (0x100be8) and
__do_global_dtors_aux (0x100ba4). No TEXTREL, RPATH, RUNPATH, C++ stream
construction, host wrappers or fault selectors appear. Integer division
helpers are linked internally from libgcc, without another dynamic library.
Body storage is exactly 586 bytes.

Compared with the 586-byte stdio reader, 19 required function names are new:
__get_errno_ptr, clock_gettime, close, fstat, getpid, getppid, lseek, memset,
open, read, readlink, sigaction, sigaddset, sigemptyset, sigprocmask,
sigwaitinfo, strlen, vsnprintf and write. Availability of those symbols does
not itself prove native signal behavior or runtime stability.

## SDK ABI capture

The separately compiled hold_api.o exposes these sizes and offsets without
executing ARM code. Its declarations are consistent with hold_api.i:

| SDK item | Bytes |
| --- | --- |
| off_t, signed 32-bit | 4 |
| ssize_t | 4 |
| struct stat | 72 |
| stat.st_size offset | 8 |
| siginfo_t | 40 |
| siginfo_t.si_pid offset | 12 |

The raw lseek signature uses this four-byte off_t. In the actual reader,
the offset is passed in r1 and whence in r2; the returned signed 32-bit
value is sign-extended for the 64-bit log field. The sender PID is loaded
from siginfo+12. The SDK capture is private review input; neither its vendor
preprocessed declarations nor compiled objects are committed to GitHub.

## Compiled flow checked

Fifty-eight exact instruction sites and their surrounding flow were checked.
The [audit metadata](../tools/open-handle-expiry/audit-build-2026-11-26.json)
records the addresses, instructions and purposes.

- Help/default branches before active identity/file/signal work. Parent PID
  is checked with getppid. Fixed path formatting, lstat types, exact readlink
  target, O_RDONLY open and descriptor fstat/586-byte checks are retained.
- SIGALRM is defaulted and unblocked; setup alarm is five seconds. QNX
  SIGUSR1 is 16, blocked before file access and reset to default while
  blocked. The hold alarm is 18 seconds before HELD is written.
- Raw read requests 100 bytes, requires exactly 100 and compares its prefix.
  Raw SEEK_CUR requires offset 100. The synchronous sigwaitinfo call clears
  a 40-byte siginfo object, retries EINTR, requires signal 16 and checks the
  sender against the original parent PID before RELEASED.
- Each post-release read/seek has a three-second phase bound. Raw reads ask
  for 64 bytes; each operation must return -1 and have measured latency below
  3000 ms. Anomalous success branches to bounded close instead of another
  probe. Failure errno is captured before clocks or formatting can change it.
- The alarm helper uses the monotonic start, a 25-second remaining-time
  budget rounded up to whole seconds, and the smaller phase cap. Internal
  division helpers implement its arithmetic. Rounding is not a precise
  25-second containment guarantee; a later independent controller watchdog
  and native signal behavior still require validation.
- Output uses a fixed 256-byte formatting buffer, rejects negative/oversize
  lengths, writes directly to stdout, retries EINTR and advances partial
  writes. Zero/error output fails. Close has a separately rearmed bound and
  its result is recorded without treating successful close as provider life.

No raw read result has been obtained on QNX from this new executable. Its
host-injected errors and signal tests remain host tests.

## Result and next step

The source and compiled reader pass this static review. No further Ubuntu
rebuild is required for this revision. Preserve the uploaded review archive
and existing build output. The frozen preparation package/checksums are
unchanged; this audit is a subsequent separate record.

Before preparing any target trial, implement and test the controller and
complete trace assessor. They must validate HELD readiness, exact owned
child identities, normal provider exit/reaping, endpoint absence and the
100-byte control trace before release; capture both output streams, enforce
a whole-trial deadline, and bound child cleanup with explicit failure
results. Reader exit 0 is an observation, not a complete test PASS.

The tested endpoint remains unchanged and need not be rebuilt. No new
reader RAM transfer, execution or provider-death result has occurred. The
new reader is not yet a vehicle-ready package. Larger sizes and forced
provider death remain separate tests. No plugin, XML, RPM request or HMI
operation is authorized by this build record. Actual plugin/HMI trials
remain paused; live RPM is unverified.
