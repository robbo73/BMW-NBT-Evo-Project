# Offline held-descriptor expiry assessor

Owner-supplied Claude contribution, reviewed and amended 26 November 2026.
See [REVIEW.md](REVIEW.md) and [PROVENANCE.json](PROVENANCE.json) for attribution,
original fingerprints and the five added regression checks. Current suite:
**50 passing synthetic tests**, not a QNX or vehicle result.

```sh
python3 -B -m unittest discover -s tools/held-expiry-assessor -p test_assess_held_expiry.py -v
python3 -B tools/held-expiry-assessor/assess_held_expiry.py --input capture.hxc
```

Default/help reads no file. Explicit --input reads one local capture, bounded
at 64 KiB, 2000 lines and 512 bytes per line, and produces JSON. Exit 0 plus
PASS requires the complete proposed contract; all failures exit 1. Input and
controller claims are not authenticated. Errno values are not assumed, but
must fit the actual SDK type and agree with the syscall result.

The [contract](LOG-CONTRACT.md) is still **proposed**. No target controller
implements it and no target-ready package is provided. Its mandatory
CONTROL_TRACE_OK record requires controller-side validation before release;
the final assessor also checks the provider trace independently. Watchdog
coverage, whole-trial time and real causal sequencing cannot be established
by these records alone. Native source/compiled/runtime review remains needed.

All examples are explicitly SYNTHETIC. The passing example demonstrates only
the parser's expected format; never present it as BMW evidence. The reader
and endpoint binaries/source, frozen packages and hidden stages are unchanged.
No plugin, XML, RPM or HMI behavior is tested by this tool.
