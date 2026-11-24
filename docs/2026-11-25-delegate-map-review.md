# CDS delegate-map assignment — 25 November 2026

A third-party repository review raised whether patch 0005 adds two callback
entries because subscription and async-get use the same property/delegate.
This independent static check resolves the local map question against the
original captured libAppFramework.A.so, SHA-256
057618b81375564f5255308a3c59111dd1e9eb57e43e38b7a858bff04ab41ce5.
No source patch, new build or target execution was performed.

## Result: one mapped delegate value per property

Both wrappers call the same exported
bmw::Map<BasicString<char>, CdsDelegate>::operator[] at ELF VA 0x91c0 on
app+0x128. It calls getAssocAt at 0x85bc. That helper hashes the string,
walks the bucket's association chain and compares keys using strcmp
(0x8648 through the verified PLT target 0x4eb8).

When an association exists, operator[] branches from 0x91e0 directly to
0x9250 and returns association+0x0c. Only the missing-key branch reaches
newAssoc at 0x9218 (target 0x90e0), initializes the key and links a new
association into the bucket. A hash collision can extend the bucket chain;
that is not multiple callback values for the same matching key.

The subscription wrapper at 0x7f8c calls operator[] at 0x7fa8, copies two
32-bit delegate words at 0x7fb4/0x7fb8, then invokes connector virtual +0x9c.
The async-get wrapper at 0x7fd8 first invokes connector virtual +0x94,
then calls operator[] at 0x8008 and copies the two delegate words at
0x8010/0x8014. For an existing matching property this overwrites the same
mapped value. It does not append a delegate to a per-property list.

For patch 0005's subscribe-then-get sequence using the identical delegate,
this second assignment restores the same two words to the same callback
slot. Map insertion/assignment is therefore not itself a source of double
registration. There is no evidence here requiring a different delegate or
source correction to address that particular concern.

## Limits: this is not a callback-count or concurrency proof

Subscription delivery and a get response remain distinct operations. They
can independently deliver callbacks, including identical values. This map
finding does not prove one callback total, a fresh sample, a physical query
for every API call, or successful engine-speed publication.

The get wrapper's connector-before-assignment ordering remains relevant.
The preceding subscription has already stored this identical delegate in
the reviewed sequence, but this does not establish general synchronous/
asynchronous behavior, thread safety, atomicity or lifetime/unbind behavior.
No surrounding C++ ABI or HMI execution guarantee follows from this result.

Fourteen exact ARM instructions and the strcmp PLT target were checked
against the original file. See the
[audit metadata](2026-11-25-delegate-map-audit.json). Private annotated
original disassemblies remain outside Git. No BMW binary is committed.

Actual plugin loading and HMI activation/restart trials remain paused;
live engine-speed callbacks and cluster agreement remain unverified.
