#!/usr/bin/env python3
"""Local-only assessment of one captured 586-byte rehearsal; never contacts QNX."""
import argparse
import json
from pathlib import Path
import re
import sys

FINAL = 'PASS: 586-byte dummy reader/expiry/cleanup; trace requires assessment'
SUMMARY = re.compile(r'TRACE_SUMMARY events=(\d+) dropped=(\d+) overflow=(\d+) elapsed_ms=(-?\d+)')
READ = re.compile(r'TRACE_READ index=(\d+) before=(-?\d+) requested=(-?\d+) xtype=(\d+) count=(\d+) after=(-?\d+) rc=(-?\d+)')
SEEK = re.compile(r'TRACE_SEEK index=(\d+) before=(-?\d+) offset_bits=([0-9a-fA-F]{16}) whence=(-?\d+) after=(-?\d+) rc=(-?\d+)')
READY = re.compile(r'READY pid=([1-9][0-9]*) path=/dev/nbt_large_endpoint_586\.\1 bytes=586 lease_ms=10000')


def assess(text):
    lines = text.splitlines()
    required = [FINAL, 'Stdio reader exit: 0', 'Endpoint server exit: 0',
                'PASS: larger-reader-1; bytes=586 items=1; seek-end/tell/rewind/read/close',
                'DANGLING: dummy alias remains a link; target unavailable',
                'CLEANED: dummy alias and owned fixture directory']
    for marker in required:
        if lines.count(marker) != 1:
            raise ValueError('missing or repeated completion marker: '+marker)
    if sum(bool(READY.fullmatch(line)) for line in lines) != 1:
        raise ValueError('expected one matching 586-byte helper READY line')
    if any(line.startswith(('STOP:', 'WATCHDOG:')) for line in lines):
        raise ValueError('failure/fallback reported by runner')
    summary = None
    records, reads, seeks = [], [], []
    for line in lines:
        if not line.startswith('TRACE_'):
            continue
        match = SUMMARY.fullmatch(line)
        if match:
            if summary is not None:
                raise ValueError('multiple trace summaries')
            summary = tuple(map(int, match.groups()))
            continue
        match = READ.fullmatch(line)
        if match:
            index, before, requested, xtype, count, after, rc = map(int, match.groups())
            if not (-(2**31) <= requested < 2**31 and 0 <= xtype < 2**32):
                raise ValueError('read request fields exceed captured SDK types')
            if not 0 <= count <= 586:
                raise ValueError('read count exceeds compiled body bounds')
            if count:
                if rc != -1 or before < 0 or requested < count or before+count > 586 or after != before+count:
                    raise ValueError('read record violates reviewed callback bounds/reply contract')
            elif after != before:
                raise ValueError('zero-count read changed offset')
            records.append(index)
            reads.append({'index':index,'before':before,'requested':requested,'xtype':xtype,
                          'count':count,'after':after,'rc':rc})
            continue
        match = SEEK.fullmatch(line)
        if match:
            index,before,bits,whence,after,rc = match.groups()
            records.append(int(index))
            seeks.append({'index':int(index),'before':int(before),'offset_bits':bits,
                          'whence':int(whence),'after':int(after),'rc':int(rc)})
            continue
        raise ValueError('malformed or unknown trace record')
    if summary is None:
        raise ValueError('missing trace summary')
    events,dropped,overflow,elapsed = summary
    if dropped or overflow:
        raise ValueError('trace overflow: incomplete observation')
    if not 1 <= events <= 64 or elapsed < 0:
        raise ValueError('invalid event count or unavailable elapsed time')
    if records != list(range(events)):
        raise ValueError('missing, repeated or out-of-order trace index')
    if sum(row['count'] for row in reads) < 586:
        raise ValueError('trace does not contain a complete body worth of reads')
    return {'body_bytes':586,'events':events,'dropped':dropped,'overflow':overflow,
            'elapsed_ms':elapsed,'reads':reads,'seeks':seeks,
            'read_error_records':sum(row['rc']>0 for row in reads),
            'interpretation':'Complete captured dummy trace; seek return values are SDK reply codes, not POSIX errno results.',
            'xml_parsing_verified':False,'hmi_integration_verified':False,'live_rpm_verified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,help='Chromebook tee log from exactly one completed rehearsal')
    args = parser.parse_args()
    if args.input is None:
        parser.print_help();return 0
    try:
        with args.input.open('rb') as handle:
            raw = handle.read(65537)
        if len(raw)>65536:
            raise ValueError('capture exceeds bounded 64 KiB log size')
        result = assess(raw.decode('utf-8'))
    except (OSError,ValueError,UnicodeError) as error:
        print('STOP: '+str(error),file=sys.stderr);return 1
    print(json.dumps(result,indent=2))
    print('PASS: complete 586-byte trace and runner result')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
