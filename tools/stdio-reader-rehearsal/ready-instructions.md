# Stdio-reader ready bundle — 24 November 2026

The new C-only reader passed offline ELF/import/startup review. No additional
Ubuntu rebuild is needed. This separately delivered ready package contains:

- The exact new 9306-byte nbt_stdio_reader, SHA-256
  a90b4183ea980987ca58d5a0b61f4a5ee78602272c0fba9f922f4a86ecdb0e13.
- The unchanged 13876-byte nbt_endpoint_rehearsal, SHA-256
  83c6e473829ea1441872a7f93a4693de0c7867a13fb5f2b2e42862e8490da25f.
  This is the endpoint helper that already passed native expiry/forced-death
  checks and the dummy alias checks.
- The new bounded check_stdio_alias.sh, the original reader C source and
  its 12 host checks, nine runner checks, host-only stdio failure wrappers,
  the native reader trace, offline audit metadata, package pins and hashes.

No SDK output, BMW binary, actual manifest or plugin payload is included.
The compiled helpers are distributed in this private ready archive only,
not committed as binaries in GitHub.

## Store on the Chromebook

Copy nbt-stdio-reader-ready.tar.gz to ~/bmw-idrive/ on the Chromebook.
After checking the archive against the supplied SHA-256, extract it into
its new directory and run:

```sh
cd ~/bmw-idrive/nbt-stdio-reader-ready
sha256sum -c SHA256SUMS
```

These local checks do not contact the car or execute either ARM program.
Keep all files together. Do not run an ARM executable in Chromebook Linux.
There is no need to run more Ubuntu tests after the supplied successful
cross-build; the new runner tests have passed in the cloud.

## Reviewed next vehicle sequence

Wait for the session-specific commands. The intended sequence is transfer
or reuse the two fixed OMAP RAM filenames below, refuse symlinks/existing
non-regular destinations, require full read-back hashes, and run reader
help-only startup/normal exit before considering the isolated alias test:

```text
/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e
/dev/shmem/nbt_stdio_reader_a90b4183ea98
```

The test runner defaults to help with no writes. Its only active option
is --rehearse. It is derived from the already tested dummy alias deadline
runner and creates only a fresh mode-700
/ramdisk/mm/.nbt-endpoint-alias.<shell-pid>/ directory. Its
dummy-discovery.txt symlink points to the new child helper's PID-specific
endpoint. It invokes the C reader with that shell PID instead of cat.
The C reader checks the alias and the exact dummy bytes while performing
fopen/seek-end/ftell/rewind/full-file fread/fclose. A five-second default
alarm bounds only the reader's active operation.

The runner requires reader exit 0, then helper normal deadline exit 0,
a remaining symlink whose target is unavailable, and owned-fixture cleanup.
It uses the same helper-only fifteen-second fallback and checked-empty
cleanup pattern as the previous runner; it signals no existing process.
Only the fixed alias is unlinked, and unexpected non-link replacements or
extra directory entries are preserved and cause failure. The missing QNX
rmdir utility is not used. Do not concurrently edit this protected fixture.
A changed symlink at its owned alias name may be unlinked without following
its target. Killing the shell itself with SIGKILL can leave a dummy fixture;
these traps are not a general HMI-fault recovery mechanism.

## Scope of review and tests

The actual new reader is ELF32 little-endian ARM, QNX interpreter
/usr/lib/ldqnx.so.2, only libc.so.3 required. All 22 required function imports
exist in the captured car libc, and both COPY objects match provider sizes.
There is no TEXTREL/RPATH/RUNPATH, unsupported relocation or host wrapper/
C++ stream initialization in this executable. These are static findings,
not proof of target startup, alarm timing or stdio compatibility.

The original 12 host tests remain unchanged and passed in the owner's
Ubuntu build. Nine additional Linux runner fixtures pass, including the
real reader source built for the host, failure propagation, missing/linked
reader, missing endpoint, overrun, unexpected-entry preservation and hangup.
They use ordinary host files and shortened test sleeps. They do not model
QNX IPC or validate new vehicle behavior.

The new reader/runner have not yet executed on the BMW. Neither XML parsing,
real manifest admission, HMI lifetime monitoring nor plugin initialization
is implemented. The real candidate stages remain untouched and hidden.
Library-loading/HMI activation/restart trials remain paused. Live RPM has
not been demonstrated.
