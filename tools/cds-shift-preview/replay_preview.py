#!/usr/bin/env python3
"""Host-only JSON fixture boundary; not the production B58 parser or a CDS client."""
import argparse
import json
import math
from pathlib import Path
import subprocess


def integer(value):
    if type(value) is not int or not 0 <= value <= 2**64 - 1:
        raise ValueError('time must be a uint64 millisecond integer')
    return value


def unique_object(pairs):
    out = {}
    for name, value in pairs:
        if name in out:
            raise ValueError('duplicate JSON key')
        out[name] = value
    return out


def fixture_rpm(payload):
    """Fixtures emulate the accepted-reading boundary; this is not native JSON code."""
    try:
        if isinstance(payload, str):
            payload = json.loads(payload, object_pairs_hook=unique_object)
        if not isinstance(payload, dict) or 'error' in payload:
            return None
        value = payload.get('RPMSpeed')
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 9000:
            return None
        return float(value)  # Already RPM: never divide CDS JSON by four.
    except (ValueError, TypeError, OverflowError):
        return None


def commands(events):
    if not isinstance(events, list) or len(events) > 1000:
        raise ValueError('expected at most 1000 synthetic events')
    out = []
    for event in events:
        op = event['op']
        if op == 'callback':
            ms = integer(event['received_ms'])
            rpm = fixture_rpm(event['payload'])
            out.append('discard' if rpm is None else 'sample %d %.17g' % (ms, rpm))
        elif op in ('poll', 'show', 'hide'):
            out.append('%s %d' % (op, integer(event['now_ms'])))
        elif op in ('stop', 'clock_failure'):
            out.append('stop')
        elif op == 'stress':
            out.append('stress')
        else:
            raise ValueError('unknown synthetic event')
    return '\n'.join(out) + '\n'


def replay(executable, events):
    result = subprocess.run([str(executable)], input=commands(events), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=True)
    if result.stderr:
        raise ValueError('unexpected host driver stderr: ' + result.stderr)
    return [json.loads(line) for line in result.stdout.splitlines()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--events', type=Path)
    p.add_argument('--host-binary', type=Path)
    args = p.parse_args()
    if args.events is None and args.host_binary is None:
        p.print_help()
        return 0
    if args.events is None or args.host_binary is None:
        p.error('both --events and --host-binary are required')
    try:
        if args.events.stat().st_size > 65536:
            raise ValueError('fixture file too large')
        events = json.loads(args.events.read_text())
        print(json.dumps({'synthetic_only': True, 'native_execution': False,
                          'producer_freshness_verified': False,
                          'upstream_window_ms_for_test_only': 750,
                          'results': replay(args.host_binary.resolve(), events)}, indent=2))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        p.exit(1, 'STOP: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
