# Static registry findings

Offsets below apply only to the captured vehicle firmware. They are not
instructions to dereference guessed live addresses.

Inspected files:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| libhmiplugin.so | 199520 | 2819ea3a02cdcdef571ff99586762c2871961f695d46bcee62edeeb72a1cdfeb |
| libhmicom.so | 159028 | 639fd263febd3a53940cf0735c562dbda5c19c0ccb08bb5c806befe565fda1db |

The useful registry implementation is in libhmiplugin.so. Its
getInstanceCacheByIdentifier at ELF VA 0x17d90 looks up an interface name in a
global hash table at module-relative offset 0x30614. The native function can
allocate a missing entry; the reader never calls it. It reads an existing
hash bucket for the ASCII name ICarDataServer only. The captured GNU
libstdc++ string hash at 0x53ff8 uses FNV-1a for this ASCII input.

The registry table has bucket pointer/count/entry-count at +8/+12/+16.
Nodes hold key data pointer, cache pointer and next node at +0/+4/+8.
getCurrentTLS at 0x17b94 shows the per-scope table at cache+0x18/+0x1c/+0x20.
notifyPluginAvailable at 0x16930 stores the existing interface at TLS+8.

For the expected primary CCarDataMainProvider interface, the constructor at
libhmiremoting ELF VA 0x19bdd0 stores its CDS environment at provider+0x1c.
CCdsEnvironment::getProxy(0), at 0x1f4f2c, obtains Vehicle from environment+4.
The RPM property factory at 0x1efa40 binds Vehicle+0x4508. The getter reads
status at proxy+0x60 and raw u16 at proxy+0x78. The property coding check
uses proxy+0x10. These are internal fields, not UDS diagnostic identifiers.

Six expected vtable address points are checked before interpreting objects.
The offline audit confirmed those against symbol tables, four source-file
fingerprints, the registry location and sixteen ARM layout instructions.
The earlier RPM audit separately confirmed the exact property registration,
JSON format, 0.25 scaling and special raw value 65535.

This establishes a candidate read-only inspection path. It does not establish
that ICarDataServer is currently cached, that the engine-speed proxy is valid
or fresh, or that a live CDS subscription works. No target program was run
during this review.
