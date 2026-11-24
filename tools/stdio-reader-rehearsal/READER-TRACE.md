# Native manifest read/path trace — 24 November 2026

Static analysis of the original owner-captured HmiMain3D only. Input:
58795504 bytes, SHA-256
027cf939eb503cb55048fba575b4155d28acfaec62020d40d6ea1caa3204b8cf.
The original file is unchanged. Addresses below are ELF virtual addresses,
not addresses to invoke on the running HMI. No native routines are executed.

## Admission and reader entry

The directory scanner calls stat on a candidate manifest at 0x2439678;
nonzero return branches at 0x24396b4 to the skip path. The mode check at
0x24396b8..0x24396c4 excludes directories, not symlinks as such. This is
followed lookup; it is not evidence that every later admission step succeeds.

The managed record stores the discovery directory at object+0x20 and the
manifest filename at +0x24 (constructor assignments at 0x243bb98/0x243bba4).
The loader at 0x243c424 combines directory, delimiter and manifest name,
then calls the file loader at 0x298a570 from 0x243c5bc. Nearby diagnostic
strings identify tinyxml.cpp and LoadFile; this is a TinyXML-style loader.
No exact upstream TinyXML version is asserted.

## File sequence before XML parsing

| Call site | Observed operation |
| --- | --- |
| 0x298a5ac | fopen(path, "rb") |
| 0x298a5c0 | fseek(stream, 0, 2), SEEK_END |
| 0x298a5c8 | ftell(stream), save returned length |
| 0x298a5dc | fseek(stream, 0, 0), SEEK_SET |
| 0x298a620 | allocate length+1 bytes |
| 0x298a638 | fread(buffer, length, 1, stream) |
| 0x298a63c | require one complete item, not a byte count |
| 0x298a674 | fclose on the successful full-read branch |
| 0x298a67c | NUL-terminate the buffer at its length |
| 0x298a7c8 | dispatch the in-memory parsing virtual after line-ending processing |

The captured loader does not check the two fseek return values at these
call sites. The new inert reader deliberately checks them, rejects a length
other than exactly 23, uses a fixed stack buffer and requires the known
bytes. It reproduces the successful stdio access pattern, not the native
allocation, newline conversion, XML parsing, or unchecked error behavior.

A successful cat on the target establishes stream reads but does not prove
SEEK_END/ftell/rewind support. This is the concrete reason for the separate
C-only reader test. The existing endpoint retains the SDK's lseek default;
its actual compatibility with this sequence remains unverified.

The unwind index coalesces this reader with many unrelated routines.
Analysis therefore follows the direct call at 0x243c5bc and its instructions
starting at 0x298a570, not the entire unwind range as one function.

## Path expansion and lifetime implication

The parameter parser at 0x243c0e8 searches values for the literal
{pluginDir}. Both ordinary tags and name/value parameter forms can replace
that token with the managed record's directory field (+0x20); direct tag
replacement occurs around 0x243c1e0..0x243c230. Without the token it stores
the supplied value instead (0x243c254..0x243c264).

The code-file field is extracted at 0x243c8fc and stored at +0x28. During
init, the path-token search at 0x243cb98 can replace it using +0x20. The
existing-path check at 0x243cc08 skips to the load path at 0x243ce1c on
success. On failure, a fallback constructs parent/lib+stem+.so before
bmw::DynamicLibrary::load at 0x243ceb4. Thus a future explicit existing
absolute library path is a candidate for avoiding that fallback; this has
not been tested in HMI.

These findings support keeping discovery lifetime separate from payload/
resource lifetime. They do not establish that removing discovery will
unload existing code, that all resource loading paths are covered, or that
a real manifest or C++ plugin can be used safely. No manifest is transformed
by this package, and both existing candidate stages remain untouched.

## Captured libc availability, not a completed ELF import audit

The actual libc.so.3 (SHA-256
7d1199d75bd1187dc3e1842fa89320e9eb82d7215ccf4ce251edcf033cf46baf)
exports the planned calls. Examples: fopen 0x505e4, fseek 0x50de8,
ftell 0x50f98, fread 0x50ae8, fclose 0x4fc58, lstat 0x19d84,
stat 0x19d7c, signal 0x19b64 and alarm 0x15f18. These values were read
from PT_DYNAMIC because this libc lacks the normal section table.
The actual rebuilt reader still needs its own ELF/import/initialization
review; this preliminary symbol check does not replace it.
