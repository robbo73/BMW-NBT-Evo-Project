# Follow-up to the owner's independent repository review — 25 November 2026

The owner supplied Claude's report of six passing scratch-copy suites and
suggestions about runtime failures, file sizes, delegate storage, Sports
Displays observation and a concise status page. The rerun is recorded as
an external report; the unchanged suites were not needlessly rerun here.

## Actions completed

- Added [STATUS.md](../STATUS.md) with separate vehicle, static-review and
  unverified states, evidence links and current blockers.
- Independently traced the actual captured framework's shared callback map.
  [Same-key assignments overwrite one delegate value](2026-11-25-delegate-map-review.md);
  they do not append callbacks. Fourteen instruction sites and strcmp target
  were verified. No source patch or new build is justified by this map concern.
- Confirmed the frozen init-check manifest is 586 bytes, not multiple KB.
  Its 10951-byte UI description is separate. Larger body testing is still
  useful: every successful native endpoint/read rehearsal so far used 23 bytes.

## Important interpretation boundaries

The RAM endpoint work proves unavailability to subsequent tested lookups
when its helper expires/dies. It does not bound execution time of an app
already loaded into HMI, solve the earlier mixed-runtime crash, or prove
fault containment across an HMI-only restart. Guard identity/lifetime,
real XML admission and resource/handle lifetime still need review.

A Sports Displays closed/open comparison is a useful potential control.
However, those two proxies are different native functions from CEngineSpeed2.
Valid/changing sport data alongside invalid RPM would confirm those sport
channels, not prove an RPM publisher exists or identify bind as the sole
remaining cause. Absence of change may also reflect a consumer that remains
registered after leaving the screen. Listener counts, valid bits and cached
bytes alone do not prove actual transmission, freshness or matching cluster
values. Do not replay the stock screen's state events as a diagnostic command.

## Suggested bounded request for Claude

The next independent task can stay offline and reuse the repo's own C source:

> Review tools/endpoint-rehearsal/nbt_endpoint_rehearsal.c and endpoint_policy.c,
> the stdio-reader trace, and STATUS.md. Identify assumptions tied to the fixed
> 23-byte body and review what must change before a bounded larger-file inert
> rehearsal. Consider a 586-byte manifest-sized body and sizes around 2048
> bytes, plus 4096/8192, partial and full-item reads, SEEK_SET/CUR/END, EOF,
> negative/overflow offsets and provider death with an open client handle.
> Distinguish incoming msg_max_size from actual reply limits; do not assume
> either. Cite exact source/SDK requirements, propose focused offline checks
> and state unknowns. Do not activate a plugin, alter firmware, or infer live
> RPM. The real manifest/XML parser and HMI lifetime guard remain untested.

This focuses limited independent-review time on the next concrete gap.
The delegate-map result is already available for optional cross-checking.
A stock-screen reader extension is a separate optional task, requiring its
own bounded reads/fingerprints and offline review before vehicle use.

This follow-up changes documentation and static audit metadata only. Frozen
archives, source patches, build outputs and hidden vehicle stages are not
modified. No new QNX build or vehicle command was performed. Actual plugin
loading and HMI activation/restart trials remain paused; live RPM remains
unverified.
