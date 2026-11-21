# Volatile-path recovery investigation — 21 November 2026

This is preparation, not a vehicle activation procedure. No trial link or
RAM payload has been created and no new plugin has been loaded. The
initialization-check candidate remains in the verified hidden disk stage.

## Current vehicle baseline

Owner-provided console output shows HmiMain3D PID 294966 with:

| Mapping | Address |
| --- | --- |
| AppFramework.A.so (name truncated by pidin) | 0x7812f000 |
| CoreFramework.A.so | 0x785e4000 |
| libstdc++.so.6 | 0x78970000 |

The same filtered output contained no NbtAad mapping. The app RAM log was
absent. The broad `grep -l 210` search printed no manifest matches under the
existing standard RO/RW Plugins and PluginsCoded directories. This is an
observed text search, not a parsed/global proof of no connector conflicts.
The owner reports ignition on, engine off, stable screen and battery fine;
no connected support supply was reported. No new load test has taken place.

The native OMAP mount/listing output shows:

```text
/net/hu-omap.nbtevo/dev/blk/ram-0-alloc-0-tmp on /ramdisk/mm type tmp
/net/hu-omap.nbtevo/dev/ramf0t77 on /fs/ram5 type qnx4
/tmp -> /fs/ram5
```

`/ramdisk/mm` exists as a directory with mode 1777. `/var/tmp` is absent.
These are RAM-device mount observations, not a demonstrated lifetime or
cleanup guarantee. HMI process restarts need not recreate either mount.
No reboot was requested to test clearing.

## Scanner trace from the original HMI

Offline disassembly uses the previously captured, unmodified HmiMain3D with
SHA-256 `027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf`.

- Registered-root iteration at 0x2439ee0 calls directory inspection at
  0x2439860, passing each root's coded-name-filter flag.
- Directory inspection uses opendir/readdir, builds each child path, then
  calls imported `stat` at 0x2439c2c (veneer 0x24f7718 to 0x20f218).
  A nonzero return branches at 0x2439c34 to the skip path 0x2439dd8.
  A successful result is accepted only when mode & 0xf000 is 0x4000
  (directory), at 0x2439c38–0x2439c44.
- It reaches manifest-directory inspection at 0x2439d28, calling
  0x24395d4. That routine uses opendir on the accepted child, iterates
  .manifest filenames, checks them with stat, and calls the existing managed
  plugin path at 0x24397bc -> 0x2439264.

This path uses stat, not lstat. Under standard stat semantics a directory
symlink can pass when its target exists, and a dangling target fails before
manifest parsing. No extra symlink prohibition was found between the
child-path construction and this check. This establishes a static candidate
route, not a completed symlink-admission/loading test on QNX or an audit of
every subsequent resource/path behavior.

## Recovery limits and next bounded check

A persistent link to a uniquely named RAM directory could limit discovery
after that RAM directory is cleared. It must never point to the persistent
hidden stage as a fallback. However, neither link admission nor the relevant
restart/clear behavior is verified. An HMI-only restart could leave the RAM
payload in place and discoverable, so RAM placement alone is not a recovery
procedure. Existing `nbt_init_check.py` explicitly refuses linked active
paths: its disk-stage rollback must not be applied to a proposed link-based
trial. That design needs its own guarded containment and observation plan.

The prepared `tools/init-check/check_ram_directory.sh` is an inert,
filesystem-only check: confirm the ln utility exists, create a mode-700
directory with a PID-specific name under /ramdisk/mm, write/read one text
file, and remove the file/directory. Exit/signal traps attempt cleanup. It
does not create any symlink, touch Plugins, move/modify either candidate,
execute target binaries or restart HMI. Its script was syntax-checked and
exercised locally with the fixed RAM root replaced by a disposable Linux
fixture; vehicle execution is pending. No reboot-clearing claim follows
from a successful write/read/delete result.

Library-load and restart trials remain paused. Continue preparation offline
if the owner disconnects; maintaining an ignition-on car session is not
necessary for disassembly or recovery-helper development.
