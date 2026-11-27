#!/bin/bash
# Ubuntu/Linux host only. No Docker, QNX, project edits or network operations.
set -eu
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
command -v g++ >/dev/null
command -v python3 >/dev/null
task_parent="${1:-$HOME}"
task_output="$(mktemp -d "$task_parent/nbt-cds-shift-host.XXXXXX")"
echo "Host results: $task_output"
if python3 -B test_preview.py > "$task_output/tests.log" 2>&1; then
    cat "$task_output/tests.log"
else
    cat "$task_output/tests.log"
    echo "STOP: host checks failed; preserve $task_output"
    exit 1
fi
g++ --version > "$task_output/compiler.txt"
g++ -std=c++98 -O1 -g -Wall -Wextra -Werror -fno-exceptions -pthread \
    -I. host_replay.cpp -o "$task_output/host-replay"
python3 -B replay_preview.py --events demo-events.json \
    --host-binary "$task_output/host-replay" > "$task_output/demo.json"
cp SHA256SUMS "$task_output/SOURCE-SHA256SUMS"
cp PROVENANCE.json "$task_output/PROVENANCE.json"
python3 -B - "$task_output" <<'PY'
from pathlib import Path
import hashlib, json, sys
p=Path(sys.argv[1])
r={'scope':'Linux host-only synthetic CDS/ShiftDeck model replay',
   'native_execution':False,'vehicle_connection':False,'milestone_7_edited':False,
   'producer_freshness_verified':False,'host_tests_passed':24,
   'demo_sha256':hashlib.sha256((p/'demo.json').read_bytes()).hexdigest()}
(p/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
PY
tar -czf "$task_output.tar.gz" -C "$(dirname "$task_output")" "$(basename "$task_output")"
sha256sum "$task_output.tar.gz"
echo "HOST ONLY: 24 synthetic tests and model replay passed. No QNX/BMW execution."
echo "Review archive: $task_output.tar.gz"
