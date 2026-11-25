# Reviewed 586-byte dummy-body bundle — 25 November 2026

No further Ubuntu rebuild is needed. This private ready archive contains
the exact reviewed pair, each a C-only QNX ARM executable requiring libc.so.3:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| nbt_large_endpoint_586 | 15898 | 8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2 |
| nbt_large_reader_586 | 10248 | f0d391701c69a8dd07c203c876bbed1ef5d1a885604667b4ed64502f87745884 |

The endpoint has 34 required function imports, with iofunc_lseek_default
the only addition over the old helper; the reader has 22, unchanged over
the old reader. All are exported by the captured car runtime. COPY object
sizes match, only COPY/JUMP_SLOT relocations occur, and no host wrapper,
C++ stream constructor or extra runtime library appears. The reviewed
compiled body length is 586 and the trace buffer is 64 records of 56 bytes.
These are offline findings; neither new executable has run on the BMW.

## Chromebook storage

Copy nbt-large-body-ready.tar.gz to ~/bmw-idrive/. Verify its supplied
archive hash, extract it into its new directory, then run:

```sh
cd ~/bmw-idrive/nbt-large-body-ready
sha256sum -c SHA256SUMS
```

Local checksum checks do not contact the BMW or execute ARM code. Do not
run either ARM binary in Chromebook Linux. No compiler/install is needed
there; the optional host tests were already run in the cloud/Ubuntu.
The ready bundle includes source/tests, audit/metadata and no BMW binary,
SDK output, real manifest or plugin payload. Binaries are not in GitHub.

## Next session-specific vehicle sequence

The transfer commands will require separate read-back hashes and help-only
startup/exit for both fixed OMAP RAM filenames before the active test:

```text
/dev/shmem/nbt_large_endpoint_586_8f502b6394a0
/dev/shmem/nbt_large_reader_586_f0d391701c69
```

No upload/ARM run is performed by this package itself. The active runner
check_large_alias.sh defaults to help with no writes and accepts only
--rehearse. It starts its own new endpoint child and creates a fresh mode-700
/ramdisk/mm/.nbt-large-alias-586.<shell-pid>/ directory with a dummy-body.bin
symlink. It runs the bounded C reader with that shell PID, requires reader
exit 0, then helper normal deadline exit 0, and checks the alias is dangling.
It uses the prior tested helper-only fifteen-second fallback and owned,
checked-empty cleanup pattern. No pre-existing PID or HMI is signalled.
Unexpected replacements/entries are preserved and cause failure; a changed
symlink at its owned alias name can be unlinked without following it.
Killing the shell with SIGKILL can still leave its dummy RAM fixture.

The endpoint body is position-dependent binary data including NULs. It is
not the real 586-byte manifest and is not parsed as XML. The incoming 2048
message setting is unchanged; outgoing read sizes are observed, not assumed.
The source retains the established receive-ID timeout handling and ten-second
lease. The reader checks both seeks, nonnegative/exact ftell, a full fread
item, exact bytes and close under its own five-second alarm.

## Capture and assess the complete trace

The endpoint prints TRACE_SUMMARY, TRACE_READ and TRACE_SEEK only after
detachment/destruction. A normal run is expected to take about eleven
seconds. A later Chromebook command will capture the complete SSH stdout
with tee (and Bash pipefail), then invoke the local-only checker:

```sh
python3 assess_trace.py --input PATH_TO_ONE_COMPLETE_CAPTURE
```

The remote runner's PASS covers reader/expiry/cleanup, and explicitly says
the trace still requires assessment. The Python checker additionally requires
all completion markers, a matching READY line, one non-overflow summary,
contiguous complete record indexes and bounded read counts/offsets. It prints
the actual read requests/seeks and a separate complete-trace PASS. Missing,
malformed, overflowed or partial output is refused. Logs are bounded at
64 KiB locally. Positive read error records are counted for review; seek
return values are SDK callback codes, not classified as POSIX errors by sign.
A zero observed seek count is recorded, not rejected based on an assumed
libc buffering strategy. Output includes no body byte dump.

The 36 owner-side host checks passed. Nine new runner fixtures (with the real
reader source built for Linux) and ten parser fixtures also pass. These use
ordinary files and synthetic text, not a QNX IPC/namespace/ABI emulator.
The parser's passing synthetic input is not a native trace. No extra target
code is introduced by the local checker.

The future native result can establish only the tested 586-byte dummy read
and observed requests. Other sizes, raw seek matrices, open handles across
provider death, actual XML/scanner admission, HMI guard lifetime and fault
containment remain unverified. The previous mixed-runtime fault is not
fixed by this file test. Actual plugin loading and HMI activation/restart
trials remain paused; live RPM has not been demonstrated.
