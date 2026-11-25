# Larger-body design and verification — 25 November 2026

This implements the next bounded preparation from the 25 November review.
It is separate from every existing frozen tool/package and actual manifest.

## Body and bounds

NBT_BODY_LENGTH defaults to 586. The preprocessor refuses zero/negative or
lengths above 16384. The actual generated array has exactly that length,
without a sentinel byte included/excluded by string conventions. Both
attr.nbytes and slicing use nbt_body_length(). The source body is filled
once before attach, then remains static until the provider exits.

Each 16-byte group encodes its absolute block offset as eight hex digits,
then ':', a deliberate NUL, five position-dependent letters and newline.
An independent Python oracle generates the same specification using string
formatting rather than C shifts. Host checks use a pointer plus explicit
length, not ctypes.c_char_p, and compare exact bytes including NUL.

The slice keeps negative-input refusal, EOF clamping and maximum-integer
handling. Body tests compile lengths 1, 23, 586, 2047, 2048, 2049, 4095,
4096, 4097, 8192, 8193 and 16384. EOF boundaries derive from each length.
Partial-read reconstruction, deterministic random offsets around the full
body, null outputs and readonly open masks are checked at all lengths.
Out-of-cap lengths are separately rejected by the compiler.

## Callback and trace behavior

The actual read callback is invoked through a host probe at lengths 586,
2049 and 8193. Tests check request/count clamping, context status, IOV length/
pointer, OCB advance and ATIME together. EOF/zero reads use zero parts and
zero status without OCB advance. Negative requests/offsets, unsupported
xtype and injected verification errors preserve the offset and return the
error. Incoming request fields are captured before the SDK verify helper.

The new lseek callback captures whence and the unsigned raw 64-bit offset
bits before calling iofunc_lseek_default. Raw hex preserves negative-offset
encodings without implementation-defined unsigned-to-signed conversion.
It records before/after OCB offsets and the exact default return. It does
not alter the message union, status, IOV or default result after the call.
A negative resmgr callback result is not classified as an error by sign.

Host probes deliberately overwrite the seek message union, set known reply
fields and return negative/zero/positive codes to check exact forwarding.
These are deliberately synthetic values, not a QNX seek implementation.
The fake dispatcher and structures are own host-only scaffolding, not QNX
headers, an ABI model or a namespace/IPC emulator. They are excluded from
target builds. The corrected non-null-context/negative-receive-ID timeout
cases and real receive/handler failures remain covered by nine loop tests.

Read/seek events go to a static 64-entry array. Extra events increment a
saturating dropped counter and preserve the first records. The callback
path only copies bounded fields and clears one fixed-size record; no log
IO, allocation or timestamp syscall is added inside it. Output occurs once
after resmgr detach/context free/dispatch destroy. The summary elapsed time
runs from before dispatcher setup through cleanup, before formatting/output;
a failed final clock read prints -1. It does not include body generation
before the lease or delayed output afterward. Instrumentation is not free,
and this timing is not a recovery guarantee. SIGKILL loses unprinted logs.

## Captured SDK declarations checked privately

The installed QNX 6.5 interface capture (resource_api.i SHA-256
4cf95bd71aa96177d49986e18ba05faa6e1b4b4aaa82cde50de839943f4eac51)
was used in a private 32-bit syntax-only check of the actual callback source.
The default lseek prototype is resmgr_context_t*, io_lseek_t*, iofunc_ocb_t*;
input whence is short and input offset is unsigned 64-bit. Checked offsets:
whence at +4, offset at +8, union size 16, OCB offset at +8. Callback-table
assignment type checking passed against that captured declaration set.
No vendor declaration/preprocessed output is included here. This check is
not an ARM ABI or runtime test and did not create a QNX executable.

The car libc already exports iofunc_lseek_default (ELF value 0x35968), but
this direct call is new relative to the old endpoint's import list. New
actual ELF imports/relocations/startup still require review after the Ubuntu
cross-build; source availability of one symbol is not a complete import audit.

## Reader and deferred tests

The new reader checks both seeks and rejects negative or mismatched ftell
before its bounded full-item fread. It compares binary data with memcmp
and checks close. Its 15 host tests cover canonical PID/overflow bounds,
path/link/type/size controls, exact and wrong bytes, six stdio faults,
normal reads at 586 and 8193 and a blocked read stopped by its own alarm.
All these use ordinary host files, not a native resource manager.

The initial QNX build is 586 bytes only. No native larger-size result is
claimed. It has no raw descriptor seek matrix or open-handle-at-provider-
death variant. Those need separate reviewed readers and deadlines/buffering
controls; a five-second alarm cannot cover sleeping past a ten-second lease.
No attempt is made to provoke the native HMI loader's unchecked ftell error.

No real XML, Plugins path, payload, process injection, native framework
loading, HMI restart, coding or firmware change is implemented. The old
23-byte helper/reader, plugin source and hidden stages remain untouched.

## Host wrapper compatibility follow-up

GNU/Linux libc headers can route fread through __fread_chk when fortified.
The initial read-only test wrapper intercepted only the ordinary symbol,
so a fortified host read bypassed deliberate failure/hang injection. This
was reproduced with the exact two owner-reported failures. Both symbols
are now wrapped only in host fault binaries; no QNX source/build flags
change. The ordinary and fortified wrappers share the same injection and
forward to their respective real libc entry point otherwise. Markers
confirm the selected hook was reached. A third host reader build explicitly
sets _FORTIFY_SOURCE=2 and two regressions check successful normal reading,
injected failure and a blocked read killed by the real reader alarm.
The wrapper now waits in pause repeatedly so unrelated handled signals
cannot accidentally release the deliberately blocked fault.
