# Read-only plugin-manager path inspection — 20 November 2026

After the admission observation, the owner confirmed that the 15 November
candidate remains under .nbt-rpm-stage-09902c834a37, with a 112119-byte
library and its four companion assets. The current RW alias points to
/var/opt/hmi/data/ID5. Plugins exists, and the RW-tree name search found the
NbtAad payload only inside the hidden stage. The new 112212-byte async-get
candidate has not been copied there. The listing establishes locations and
sizes, not a new content-hash verification. No files were moved.

This preserves the disabled rollback state. Its absence from the current
HMI is expected and cannot reproduce or explain the earlier failure when
the candidate was discoverable.

## Additional observer

The opt-in --inspect-manager flag requires --read-cache and reads the
existing CAppManager singleton and registered directory tree. It uses the
existing one-connection SSH/pidin/dd transport, process identity checks,
image fingerprints, byte/call limits and read deadlines. It does not invoke
a manager method, start a scan, create an entry, load a library or write
target memory/files. No new BMW executable is installed.

The exact captured HmiMain3D (SHA-256
027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf)
exports CAppManager::mInstance at 0x039f9e94 and its primary vtable address
point at 0x038e8530. Before dereferencing the singleton, the observer checks
four additional relocation-free code fingerprints from that file:

- Constructor 0x2438778, confirming manager/header layout and vtable.
- Directory iteration 0x2439ee0, confirming node path/flag offsets.
- Regular-directory registration 0x24385d0.
- BMW BasicString<char> constructor 0x10119f0, confirming its string header.

The directory tree header is at manager+0x1c: color, root, leftmost,
rightmost and count. Nodes hold color/parent/left/right, a BasicString data
pointer at +0x10 and coded-name-filter byte at +0x14. The scan routine
passes the latter flag to directory inspection. Tree count is capped at
16; parent links, pointer bounds, count, extrema, path ordering and boolean
representations are checked.

BMW BasicString's data header is **refcount/capacity/length**, unlike the
GNU COW string used in the CDS registry/property maps. Paths are read using
this verified length at data-4, capped at 512, with capacity, termination,
absolute-path and printable-ASCII checks. Every visited dynamic region is
rechecked. This is a best-effort snapshot without locks or suspension,
not an atomic view. The singleton and heap pointers are read afresh.

The two bytes at manager+0x54/+0x5c are reported as raw flags. Their full
semantics are not inferred. Reported directories are configured records;
the report does not prove a directory exists, was scanned at a particular
time, passed admission, or produced a successfully initialized plugin.
It neither changes nor reassesses the pause on vehicle load/unload probes.

## Validation

All 89 offline tests pass, including 18 new cases covering existing/empty
trees, wrong fingerprints/types, absent singleton, excessive count, cycles,
bad parent/extrema links, unordered paths, invalid flags, the wrong string
header convention, missing terminator, concurrent string changes, unchanged
fixture memory and explicit mode selection before SSH. The four profile
fingerprints and singleton/vtable export addresses were independently
checked against the original ELF; no runtime relocations fall in those
code spans. No firmware payloads are included in the tool or tests.

A real-script subprocess test also checks shared module identity: optional
inspectors now use the same Refuse type as the CLI, so their refusals reach
the saved JSON error path instead of escaping as an uncaught exception.

This new mode has not yet been exercised on the vehicle. It is intended to
identify the actual registered search paths while the candidate stays hidden.
