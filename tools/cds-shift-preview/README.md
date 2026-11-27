# Host-only CDS receipt to ShiftDeck drawing experiment

This is an isolated Linux C++98 experiment, not an installable plugin. It
changes no milestone-7 source, hidden stage, native binary or vehicle file.
It needs Python 3.8+, g++, pthreads, sha256sum and tar. No Docker, SDK or
network is used. The C++ headers refuse a QNX build.

`run_host_review.sh` verifies the frozen source checksums, runs 24 synthetic
tests, builds one **Linux** replay driver and records a small demo. All output
goes in a new unique directory under your home folder, with an adjacent
review archive. Failed checks stop and retain their output.

```sh
bash run_host_review.sh
```

When running tests directly from the Git source tree instead of the frozen
preparation, use `python3 -B test_preview.py`. Default/help of
replay_preview.py performs no replay.

## What is reused and what is simulated

Three complete methods (`animatedRpm`, `digits`, `draw`) are copied unchanged
from ShiftDeck at upstream commit
8567abaadd1305965b3ad39e3222575cd49c507d into renderer_methods.inc. Their body
hashes and the original file hash are in PROVENANCE.json. shift_assets.h
contains the matching upstream constants, including the old 5800–6700
targets. The MIT licence and ID6 Apps contributors notice are retained.

An independent host wrapper supplies input frames, a fake ImageID token and
an image-model sink. It does not construct a BMW PluginApp, implement the BMW
object ABI, send dispatcher messages, draw real pixels, read preferences,
load image ZIPs or generate assets. Unknown speed is always -1 (`--`).
No SDK header or PolyForm NBT-AAD source is included. No borrowed worker,
socket, subprocess lifecycle or diagnostic transport is integrated.

The new latch uses pthread_mutex to copy RPM, receipt time and sequence as
one snapshot. A writer accepts already-validated numeric RPM; the fixture
runner uses Python JSON validation solely to supply synthetic inputs. It is
not the production UTF-16 callback/parser and does not test their native ABI.

The sink records the unchanged renderer's model/image IDs. Tests check zero
versus missing data, 700 RPM staying 700, invalid/error payloads, rounding,
shift lights, easing, stale blanking, hidden display, clock failure fixture,
and late updates after stop while the object is still alive. A threaded test
checks 20,000 writes against concurrent atomic snapshots; writers are joined
before destruction. A stop flag is **not** proof of unsubscribe or callback
quiescence and does not make access to a destroyed object safe.

## Freshness and units are explicit limits

- CDS JSON RPMSpeed is already in RPM. Never divide it by four again.
  The existing B58 parser's 0..9000 range is preserved; conversion rounds
  once only at the integer display boundary. Fractional values are synthetic
  robustness cases; the captured native publisher formats an integer.
- There is no producer timestamp or sequence in the observed JSON shape.
  A receipt cannot distinguish a cached replay from a fresh vehicle status.
  Every report therefore has producer_freshness_verified=false.
- Polls never restamp the latch. An identical-value callback at a later time
  is a new **receipt**, not automatically a new measurement. Two callbacks
  can share a millisecond; neither changes that timestamp. Errors do not
  become zero or refresh the prior valid reading.
- drive_frame.sampled_ms carries the receipt timestamp **in this host
  experiment only**. Its upstream field name does not authenticate an actual
  sample time. Outputs call it received_ms/recent_arrival accordingly.
- The unchanged renderer blanks at age >=750 ms. This is the pinned upstream
  baseline being demonstrated, not our selected CDS staleness policy. No
  second 2.5-second telemetry-store expiry is introduced into this experiment.
  Native callback cadence/change-only behavior must be measured before a
  production policy is selected; no timeout is widened to manufacture liveness.

## Replaying a local fixture

The script's demo is equivalent to this command, using the host binary just
built in the printed result directory:

```sh
python3 -B replay_preview.py --events demo-events.json \
  --host-binary /absolute/path/to/host-replay
```

Events exercise synthetic callback receipts, UI polls, visibility, stop and
a clock-failure stop fixture. The receipt timestamp is injected for tests,
not read from a car. Model IDs cannot prove that the physical screen layout,
fonts, XML/resource loading or actual HMI thread dispatch works.

Native subscription, removal/quiescence, permission, display resolution,
initialization/finalization, runtime stability and live B58 RPM remain
unverified. Actual plugin loading stays paused. This preparation is intended
for Ubuntu only; do not transfer its host executable to the BMW.
