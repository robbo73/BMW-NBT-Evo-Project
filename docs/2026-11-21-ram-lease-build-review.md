# RAM lease rehearsal: QNX build review — 21 November 2026

The owner cross-built the separate C-only rehearsal on Ubuntu and uploaded
the resulting archive. Offline inspection passes the checks below. The
uploaded ARM executable was not executed in the cloud or on the vehicle.
This is not a plugin-load or RPM result.

## Verified identities

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| nbt-ram-lease-review.tar.gz | 14310 | a1cbc0ddee52b8fdf42e58521d941701dc70efec5ce7d9f823b1b2010729d5e5 |
| nbt_ram_lease_rehearsal.c | 6385 | 4469f32a84f8be2952fa6cf3a601250dbcdadb409f9c9173f067f0197eb3e227 |
| QNX nbt_ram_lease_rehearsal | 12820 | 12bcd2379450108198d83b1a78611337bca5902ff5728fa55bcdb01450c16238 |

The archive matches the owner's build-output fingerprint. Its exact member
set contains regular source/report/binary files and one build directory;
no links or unexpected names were accepted during extraction. C source,
test source, build script, preparation README and SHA256SUMS are byte-for-byte
identical to the previously supplied preparation package. The owner's log
records all 13 host checks passing in 2.173 seconds; the same source already
passed cloud Linux fixture and packaged-source checks. The host executable
is distinct from this uploaded QNX executable.

## ELF/runtime checks

- ELF32 little-endian ARM ET_EXEC, flags 0x5000002, entry 0x100994. The
  requested interpreter is /usr/lib/ldqnx.so.2, matching the observed QNX
  target loader route. The generic System V OS/ABI field alone is not the
  compatibility evidence.
- The only DT_NEEDED entry is libc.so.3. There are no DT_TEXTREL, RPATH or
  RUNPATH tags, BMW framework libraries, libstdc++ or libecpp dependencies.
- All **28 required undefined function symbols** are exported by the
  captured vehicle libc. The reference libc is 490310 bytes, SHA-256
  7d1199d75bd1187dc3e1842fa89320e9eb82d7215ccf4ce251edcf033cf46baf.
  Its stripped section tables omit .dynsym, so exports were independently
  read from PT_DYNAMIC/DT_SYMTAB/DT_STRTAB/DT_HASH in the original bytes.
  No input patch or section reconstruction was needed.
- The three R_ARM_COPY data objects have matching sizes in that libc:
  _Stdout 80 bytes, _Stderr 80 bytes, errno 4 bytes. The other 30 dynamic
  relocations are R_ARM_JUMP_SLOT. There is no R_ARM_REL32 relocation.
- The two optional weak imports are __register_frame_info and
  __deregister_frame_info. The single init-array entry is frame_dummy at
  0x100b50; the single fini-array entry is __do_global_dtors_aux at
  0x100b0c. Normal C runtime startup/exit is retained. There are no BMW or
  C++ stream constructors/destructors and no cleanup bypass.
- Required functions include clock_gettime, sigaction, nanosleep, lstat,
  stat, realpath, readlink, symlink, unlink, mkdir and **rmdir**. The missing
  shell utility does not imply an absent libc function: rmdir is exported
  by the captured target library. This is static availability evidence,
  not proof that each future filesystem operation will succeed.
- Compiled main at 0x100c80 is 1608 bytes. Its stat-mode access is at
  structure offset 0x2c, matching the captured HMI's stat usage. The target
  strings include only the fixed /ramdisk/mm root and --rehearse target
  switch; the host-only --host-rehearse option is absent. Default/help
  returns before filesystem setup. No dlopen, dlsym, socket, fork, process
  killing, HMI access or plugin activation call is imported.

These checks establish a consistent offline build and no missing required
exports against the captured libc. They do not prove the currently running
unit is unchanged, successful QNX startup, actual timeout duration, cleanup
after SSH loss, RAM clearing on reboot or every library/structure ABI detail.

## Frozen next-step bundle and limits

A separate `nbt-ram-lease-ready.tar.gz` contains this exact target executable,
the matching C source, offline integrity instructions, a copy of this review
and SHA256SUMS. It contains no manifest, original plugin, BMW library or
activation helper. The package is delivered separately; no binary is added
to Git. No further plugin or rehearsal rebuild is needed for these reviewed
bytes.

Ready archive: 11952 bytes, SHA-256
92fb96172c8d9f07d732bc852b2ac3090a1f346463d9c8a7272bc688c6b341d1.
Its extracted checksums and exact embedded executable bytes were verified
without executing the ARM program. The
[storage instructions](../tools/ram-lease-rehearsal/ready-instructions.md)
perform local checks only. The corresponding metadata is committed as
[audit-2026-11-21.json](../tools/ram-lease-rehearsal/audit-2026-11-21.json).

At a later connection, a new bounded vehicle step can first verify startup
with help-only, then assess the fixed ten-second inert filesystem rehearsal.
Commands and target read-back must use the frozen executable hash and the
OMAP node. No such transfer/execution was performed during this review.
The only prospective writes are a private dummy tree under /ramdisk/mm;
the staging source and registered plugin roots are not accessed.

The forced-death fixture intentionally leaves a dummy link after SIGKILL.
The rehearsal therefore does not solve guard death, prove a live recovery
mechanism, unload anything, or lift the pause on actual plugin loading and
HMI restarts. Resource lifetime, soft/full restart and lost-SSH behavior
remain part of the future containment design. No live RPM or CDS callback
has been verified. See the [preparation and host-test limits](2026-11-21-ram-lease-rehearsal-preparation.md).
