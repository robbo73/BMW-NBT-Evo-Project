#!/usr/bin/env python3
"""Offline acceptance gate for one held-descriptor trial capture. Never contacts QNX.

ACCEPT requires both: the controller (launcher) exited 0, AND the unchanged active
assessor returns PASS for the capture. A late or interrupted write can leave a
complete-looking log on disk, so a PASS alone is never accepted; the controller's
real exit status is mandatory input. The assessor is loaded by path, unmodified,
after its SHA-256 is checked against the reviewed copy.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ASSESSOR = Path(__file__).resolve().parent.parent / 'held-expiry-assessor' / 'assess_held_expiry.py'
ASSESSOR_SHA256 = '84be7de262c5d3e982d187869440e5e18364a008ecfdf58f508405408b59b162'
MAX_BYTES = 65536


def load_assessor(path=ASSESSOR):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != ASSESSOR_SHA256:
        raise ValueError('active assessor does not match the reviewed SHA-256')
    spec = importlib.util.spec_from_file_location('active_assessor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decide(controller_exit, raw, assessor):
    report = assessor.assess(raw)
    reasons = []
    if controller_exit != 0:
        reasons.append('controller exit status %d is not 0' % controller_exit)
    if report['verdict'] != 'PASS':
        reasons.append('assessor verdict %s' % report['verdict'])
    return {'decision': 'REJECT' if reasons else 'ACCEPT', 'controller_exit': controller_exit,
            'assessor_verdict': report['verdict'], 'reasons': reasons,
            'live_rpm_verified': False, 'hmi_integration_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-exit', type=int, help='the launcher exit status, as observed by the caller')
    parser.add_argument('--input', type=Path, help='captured controller stdout for exactly one trial')
    args = parser.parse_args(argv)
    if args.controller_exit is None or args.input is None:
        parser.print_help()
        return 2
    try:
        assessor = load_assessor()
        with args.input.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
    except (OSError, ValueError) as error:
        print('STOP: ' + str(error), file=sys.stderr)
        return 2
    result = decide(args.controller_exit, raw, assessor)
    print(json.dumps(result, indent=2))
    print(result['decision'])
    return 0 if result['decision'] == 'ACCEPT' else 1


if __name__ == '__main__':
    raise SystemExit(main())
