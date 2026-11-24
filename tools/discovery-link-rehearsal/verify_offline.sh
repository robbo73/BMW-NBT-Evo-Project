#!/bin/sh
# Ubuntu only: integrity, shell syntax, Linux fixture tests. Never executes ARM.
set -eu
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
sh -n check_discovery_link.sh
python3 -B test_discovery_link.py
echo "OFFLINE CHECKS PASSED: no ARM execution or BMW connection performed"
