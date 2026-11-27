# Runtime-binding observer: offline preparation — 27 November 2026

The next measurable gap is the running HMI's actual C++ symbol bindings.
A separate Python observer is now prepared and tested offline. It reuses
the existing vehicle-tested SSHMemory transport, runs on Chromebook Linux or
Ubuntu, and installs no executable or library on the head unit. This new
observation mode has not been run on the BMW. Plugin activation and standalone
library-loading tests remain paused.

## Why this follows the dependency review

The [eight-library review](2026-11-27-runtime-libraries-review.md) closes the
focused dependency graph and identifies BMWOTFapi's direct QNX C++ dependency.
It does not establish the actual binding or initialization sequence.

Further offline inspection confirms that libc's __cxa_atexit allocates a
24-byte record and stores the destructor at +8, argument at +12 and DSO
handle at +16. Its list head is the exported `_atexit_list` at libc+0x78b08.
That page is omitted from the historic probe core, as are the selected GOT
slots. A scan of retained core bytes recovers the already-known GNU cout
object pointer in the saved stack, but no basis for reconstructing a complete
registration list or initializer order. Missing pages are not zero-filled
evidence of a null binding.

The stock HMI defines allocation functions and has a 140-byte GNU cerr COPY
object. The C probe lacks that executable context. These facts justify
observing HMI pointers; they do not justify assuming a lookup order, changing
the compiler or replacing stock runtimes.

## Prepared observation

Source and instructions: [tools/runtime-binding-reader](../tools/runtime-binding-reader/README.md).
The [preparation evidence](evidence/2026-11-27-runtime-binding-preparation.json)
records source/profile pins, counts and the frozen archive fingerprint.

| Module | Selected pointer slots |
| --- | ---: |
| HmiMain3D | 3 |
| GNU libstdc++.so.6 | 13 |
| QNX libecpp-ne.so.4 | 9 |
| libhmibase.so | 2 |
| Total | 27 |

The profile records 35 named definitions, including selected allocation,
stream, initialization/destruction and vtable symbols. It also observes the
first word in seven configured stream-storage objects. The HMI cerr COPY
relocation is explicitly excluded from pointer-slot processing: its storage
contains an object, not an imported object's address.

Five code/header fingerprints are checked before and after observation:
HMI ELF header and Init constructor PLT stub, GNU Init constructor, QNX stream
initializer, and a stock hmibase stream initializer. Their small ranges are
consistency guards, not full mapped-image hashes. Data targets are compared
to exact named addresses from this four-module profile. Unknown/zero targets
are not followed. PLT-range targets are identified as potential trampolines;
none is called to force resolution. No constructor, destructor, CDS method
or native function is invoked.

All configured offsets are checked against captured load/writable regions.
Pointer slots and stream first words are reread for changes. The successful
synthetic snapshot uses 78 reads and 808 aligned bytes, below independent
caps of 160 reads and 8192 bytes. The inherited transport's own bounds remain.
Snapshots are best-effort and unlocked, not atomic. Existing bindings to
providers outside this small profile can legitimately be reported as unknown.

## Offline checks and owner handoff

All 16 new observer tests pass, including wrong fingerprints, missing and
conflicting mappings, COPY-vs-pointer handling, out-of-range/unaligned slots,
unknown and zero pointers, linker trampolines, changed bindings/object words,
short reads, byte/call budgets, zero-read default mode and preserved existing
output files. All 89 unchanged cache-reader tests also pass.

The first guard test exposed that a large but still user-addressable code
offset was not rejected before reading. Validation was tightened to require
fingerprints inside captured file-backed load regions, and named definitions
inside captured load regions. That regression now passes. No target execution
was involved in finding or fixing it.

The frozen preparation was re-extracted and rerun independently: 16 observer
and 89 cache-reader tests pass; the explicitly labelled fake-memory report
uses 78 reads/808 bytes. Packaging uses the source manifest only, excluding
bytecode caches produced by child Python tests. The runner suppresses bytecode
in subprocesses as well. The delivered archive contains exactly 23 regular
source/metadata files and no ELF payloads.

```text
nbt-runtime-binding-reader-prep.tar.gz
39931 bytes
SHA-256 79f167530635ed665bda242511d76ed3667b8d9ff016cb078cf242240f8be437
```

The owner can run its root `run_host_review.sh` on Ubuntu without Docker,
QNX SDK, compiler, pip, root or car connection. It saves source pins, Python
version, both test logs and an explicitly synthetic observation in a new
local archive. The current milestone-7 sources/binaries and hidden vehicle
stages remain unchanged. An independent owner run is pending at preparation.

## Limits and next decision

This tool answers a narrower question than a full loader model: what the
selected pointer slots and stream first words contain in an existing HMI
snapshot. It cannot infer complete initialization/cleanup order from those
values, reproduce omitted probe pages, establish object lifetime correctness
or certify that loading our plugin is stable. Merely completing the snapshot
never marks ABI compatibility or plugin execution as verified.

After the Ubuntu check, a later reviewed vehicle session can collect default
mappings first, then the explicit binding observation using a fresh PID.
There is no need to rerun the old dlopen probe or install this tool on QNX.
The result can inform the native initialization investigation; it is not
permission or evidence to resume plugin activation. Live CDS and RPM remain
unverified, and the recent stock-screen observation remains passive only.

Follow-up: the [uploaded Ubuntu review](2026-11-27-runtime-binding-ubuntu-results.md) now passes source-pin, test-log and exact synthetic-output verification. Actual vehicle bindings remain unobserved.
