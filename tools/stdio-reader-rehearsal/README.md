# Inert stdio reader: Ubuntu build for review

24 November 2026. The dummy endpoint and alias tests passed on QNX, but
cat does not exercise the seek/read sequence used by the native manifest
loader. The [static trace](READER-TRACE.md) identifies fopen("rb"), seek-end,
ftell, rewind, full-file fread and fclose before XML parsing.

This separate C-only reader is prepared to exercise those operations
against the existing 23-byte dummy endpoint through its isolated RAM alias.
It parses no XML, serves no manifest, loads no library and performs no HMI,
CDS, diagnostic or plugin operation. No manifest or candidate is edited.
The tested endpoint binary and milestone-7 source/binaries remain unchanged.

## Run on Ubuntu only

From the extracted nbt-stdio-reader-prep directory:

```sh
bash build_review.sh
```

The script verifies package checksums, runs 12 Linux tests with the host C
compiler, then uses the existing qnx65-armv7-toolchain:4.9 image to build
only nbt_stdio_reader.c with the QNX ARM GCC C driver. It does not link the
host fault wrappers or any SDK/vendor library copy. It records ELF headers,
interpreter/dependencies, symbols and hashes, then creates:

```text
/home/rob/nbt-stdio-reader-review.tar.gz
```

Upload that archive for offline inspection. Do not run the ARM output on
the BMW yet. Existing build-qnx or review archive paths are refused; keep
partial outputs if the build fails and share the error. Only this preparation
directory is mounted in Docker, not milestone-7. No SSH or target execution
is implemented in this build script. No new dependencies are installed.

## Prepared executable behavior, not yet tested on QNX

Default/help prints usage and performs no file reads. The only active
option would be --read-alias SHELL_PID. It accepts a canonical decimal PID
from 2 through 2147483647 and constructs only:

```text
/ramdisk/mm/.nbt-endpoint-alias.<SHELL_PID>/dummy-discovery.txt
```

It requires a non-linked directory, a symlink at the fixed alias name and
a followed regular file with exactly the expected size. It opens read-only,
seeks to end, requires ftell==23, rewinds, requires one complete fread item,
checks every expected byte and closes the stream. Wrong bytes are not echoed.
It creates/deletes no file, accepts no arbitrary path and signals no other
process. The five-second alarm has its default action in this disposable
reader only; a stall terminates the reader rather than reporting success.
The host alarm test does not establish timing on QNX.

A later reviewed shell runner would start the known endpoint, create the
same dummy alias outside every plugin root and pass its own shell PID to
this client while the endpoint is alive. No such target run is requested
by this package. No new XML endpoint or real plugin guard is implemented.

## Host test scope

Twelve tests cover normal exact-byte read without file changes, default/
help, malformed modes/PIDs and overflow, PID upper bound, non-link alias,
linked parent, dangling alias, directory target, wrong lengths, wrong
same-size content, six injected stdio failures and a blocked read terminated
by the reader's alarm. The test harness changes only the fixed root literal
in a temporary source copy and compiles it for Linux. A separate host-only
linker-wrapper file injects failures; it is never included in the QNX build.
These tests exercise C control flow and host stdio, not QNX IPC, namespace,
ARM ABI, XML parsing or HMI integration.

The new reader has not been cross-built or run on the car at preparation
time. Vehicle library-loading and HMI activation/restart trials remain
paused. A later successful dummy stdio read would still not prove real
manifest admission, resource lifetime or stable C++ initialization. Live
B58 RPM remains unverified.
