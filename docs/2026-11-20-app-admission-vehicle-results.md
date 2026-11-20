# App-admission observation: vehicle results — 20 November 2026

The owner updated the existing Chromebook checkout to 3f1fb54. All ten
client-file checksums passed. The read-only --inspect-admission run then
completed against the current HmiMain3D PID 278582, with 4356 bytes read in
172 bounded process-memory reads. No plugin was loaded, native API invoked,
coding edited or HMI restart requested by this tool.

## Observed result

One cached CHmiVariantServer instance was inspected:

| Predicate | Observed result |
| --- | --- |
| Direct VA 0x1a0 / A4A_REMOTE_APPS | true; coding data available |
| Derived EVA 0x9c56 | true |
| Combined admission predicate for this instance | true |
| Cached remote-HMI IVA | populated, true |
| Cached apps IVA | populated, true |
| Cached touch-command IVA | populated, false |

The instance had role value 1. Scope address was 0x03a96a68 and instance
address 0x000fbe98. These are recorded observations, not reusable addresses.
Code fingerprints, object/layout checks and best-effort region rechecks
completed without a refusal. The snapshot is not atomic.

Both alternatives used by the traced CSpecialAppsHelper predicate were
true in this instance. These results provide no basis for changing those
coding settings to try to enable the plugin.

The tool explicitly reports app_manager_scope_association_verified=false
and plugin_loading_verified=false. We have not associated this cached
instance with the exact app-manager execution scope. Even a verified pass
at that stage would not validate directory scanning, manifest parsing,
connector construction, library binding, lifecycle initialization or CDS.
The missing plugin mapping from earlier activation tests remains unresolved.

## Incidental RPM cache observation

The existing cache mode also sampled one CDS provider three times. Every
sample was raw u16 zero, status_valid=false and cached_rpm=null; freshness
was unverified. This is not a valid measured zero RPM. Engine state was not
separately confirmed for this run, so it is not treated as an additional
engine-off or idle comparison. Property presence and function-block state
were not inspected by this invocation.

## Next read-only check

Confirm the current plugin-file locations and hidden rollback state before
continuing the discovery/initialization investigation. The new async-get
candidate remains on Ubuntu, and the earlier vehicle loading/probe pause
remains in effect. A disabled hidden candidate being absent from the current
process is expected; that alone would not reproduce the old loading failure.

The source is the owner's uploaded terminal transcript and its completed
JSON report, saved on the Chromebook as
~/bmw-idrive/nbt-app-admission-20261120-1.json. The original transcript and
parsed report are retained separately. This checkpoint records summarized
predicates; no firmware or raw coding buffers are included. No direct
cloud-to-vehicle connection was used.
