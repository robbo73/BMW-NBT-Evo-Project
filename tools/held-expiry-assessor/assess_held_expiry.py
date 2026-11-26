#!/usr/bin/env python3
"""Offline assessor for one captured held-descriptor expiry trial log.

Implements the PROPOSED held-expiry-log/1 contract (see LOG-CONTRACT.md).
Reads one local file, writes a JSON assessment, never contacts QNX or the
network. A PASS is a statement about the supplied text only: the capture is
not authenticated, and nothing about HMI, plugins or live RPM follows.
"""
import argparse
import json
from pathlib import Path
import re
import sys

CONTRACT = 'held-expiry-log/1'
CONTROLLER_REVISION = 'held-controller-1'
PROPOSAL_REVISION = 2
PROVIDER_BIN = '/dev/shmem/nbt_large_endpoint_586_8f502b6394a0'
READER_BIN = '/dev/shmem/nbt_hold_reader_586_9a54c7f4dba5'
BODY_BYTES = 586
LEASE_MS = 10000
PROBE_BOUND_MS = 3000
MAX_BYTES = 65536
MAX_LINES = 2000
MAX_LINE_BYTES = 512
STREAMS = ('provider.stdout', 'provider.stderr', 'reader.stdout', 'reader.stderr')
PROBES = ('read64_a', 'seek_start', 'read64_b')
OBSERVED = 'OBSERVED: held-reader-1; three probes failed; requires provider/trace assessment'
STOP = 'STOP: held-reader-1 incomplete or unexpected result'
SIGNAL_NAMES = {9: 'SIGKILL', 14: 'SIGALRM', 15: 'SIGTERM', 16: 'SIGUSR1'}

# Most severe first. The verdict is the most severe category found; PASS only if none.
PRECEDENCE = ('MALFORMED', 'CONTRADICTORY', 'ABORTED', 'TIMEOUT_OR_TERMINATED',
              'UNEXPECTED_PROBE_RESULT', 'PREREQUISITE_FAILED', 'INCOMPLETE')

INT = r'(-?(?:0|[1-9][0-9]{0,18}))'
PID = r'([1-9][0-9]{0,9})'
STATUS = r'(0|[1-9][0-9]{0,2})'
PATH = r'(/[A-Za-z0-9_./-]{1,200})'

CONTROLLER = {
    'BEGIN': re.compile(r'contract=([A-Za-z0-9_./-]{1,40}) controller=([A-Za-z0-9_.-]{1,40}) '
                        r'controller_pid=' + PID + r' provider_bin=' + PATH +
                        r' reader_bin=' + PATH + r' fixture=' + PATH),
    'PROVIDER_STARTED': re.compile(r'pid=' + PID),
    'PROVIDER_READY': re.compile(r'pid=' + PID + r' path=' + PATH),
    'ALIAS_CREATED': re.compile(r'path=' + PATH + r' target=' + PATH),
    'READER_STARTED': re.compile(r'pid=' + PID + r' parent=' + PID + r' provider=' + PID),
    'HELD_OBSERVED': re.compile(r'reader=' + PID),
    'PROVIDER_REAPED': re.compile(r'pid=' + PID + r' status=' + STATUS),
    'ENDPOINT_ABSENT': re.compile(r'path=' + PATH + r' alias=(dangling)'),
    'CONTROL_TRACE_OK': re.compile(r'provider=' + PID + r' events=(2)'),
    'RELEASE_SENT': re.compile(r'reader=' + PID + r' signal=(USR1)'),
    'READER_REAPED': re.compile(r'pid=' + PID + r' status=' + STATUS),
    'WATCHDOG_CANCELLED': re.compile(r''),
    'WATCHDOG_FIRED': re.compile(r'target=(provider|reader|both)'),
    'ABORT': re.compile(r'reason=([a-z0-9_]{1,40})'),
    'SECTION_BEGIN': re.compile(r'stream=([a-z.]{1,20}) bytes=(0|[1-9][0-9]{0,5})'),
    'SECTION_END': re.compile(r'stream=([a-z.]{1,20})'),
    'FIXTURE_CLEANED': re.compile(r'path=' + PATH),
    'END': re.compile(r'result=(complete|aborted)'),
}
RECORD = re.compile(r'HXC1 seq=([1-9][0-9]{0,4}) ([A-Z_]{3,20})(?: (.*))?')

EXPECTED_EVENTS = (['BEGIN', 'PROVIDER_STARTED', 'PROVIDER_READY', 'ALIAS_CREATED',
                    'READER_STARTED', 'HELD_OBSERVED', 'PROVIDER_REAPED', 'ENDPOINT_ABSENT',
                    'CONTROL_TRACE_OK', 'RELEASE_SENT', 'READER_REAPED'] +
                   [name for stream in STREAMS for name in ('SECTION_BEGIN:' + stream, 'SECTION_END:' + stream)] +
                   ['FIXTURE_CLEANED', 'WATCHDOG_CANCELLED', 'END'])

# Provider formats copied from trace_log.c / nbt_large_endpoint.c (unchanged).
P_READY = re.compile(r'READY pid=' + PID + r' path=/dev/nbt_large_endpoint_586\.' + PID +
                     r' bytes=(\d+) lease_ms=(\d+)')
P_SUMMARY = re.compile(r'TRACE_SUMMARY events=(\d+) dropped=(\d+) overflow=(\d+) elapsed_ms=' + INT)
P_READ = re.compile(r'TRACE_READ index=(\d+) before=' + INT + r' requested=' + INT +
                    r' xtype=(\d+) count=(\d+) after=' + INT + r' rc=' + INT)
P_SEEK = re.compile(r'TRACE_SEEK index=(\d+) before=' + INT + r' offset_bits=([0-9a-f]{16}) whence=' +
                    INT + r' after=' + INT + r' rc=' + INT)
P_DETACHED = re.compile(r'DETACHED reason=([a-z-]{1,20}); endpoint server exiting')

# Reader formats copied from nbt_hold_reader.c format strings (unchanged).
R_FORMS = (
    ('CONTROL_BEGIN', re.compile(r'CONTROL_BEGIN name=(read100|seek_current)')),
    ('CONTROL_END', re.compile(r'CONTROL_END name=(read100|seek_current) rc=' + INT + r' errno=' + INT)),
    ('HELD', re.compile(r'HELD pid=' + INT + r' parent=' + INT + r' provider=' + INT + r' offset=100')),
    ('RELEASED', re.compile(r'RELEASED sender=' + INT)),
    ('OP_BEGIN', re.compile(r'OP_BEGIN name=(read64_a|seek_start|read64_b|close)')),
    ('OP_END', re.compile(r'OP_END name=(read64_a|seek_start|read64_b|close) rc=' + INT +
                          r' errno=' + INT + r' elapsed_ms=' + INT)),
    ('OBSERVED', re.compile(re.escape(OBSERVED))),
    ('STOP', re.compile(re.escape(STOP))),
)
R_TEMPLATE = ([('CONTROL_BEGIN', 'read100'), ('CONTROL_END', 'read100'),
               ('CONTROL_BEGIN', 'seek_current'), ('CONTROL_END', 'seek_current'),
               ('HELD', None), ('RELEASED', None)] +
              [(kind, name) for name in PROBES + ('close',) for kind in ('OP_BEGIN', 'OP_END')] +
              [('OBSERVED', None)])


class Malformed(ValueError):
    """Input cannot be parsed under the contract; assessment stops."""


class Assessment:
    def __init__(self):
        self.findings = []

    def add(self, category, message):
        assert category in PRECEDENCE
        self.findings.append({'category': category, 'message': message})

    def verdict(self):
        present = {f['category'] for f in self.findings}
        for category in PRECEDENCE:
            if category in present:
                return category
        return 'PASS'


def number(text, low=-(2 ** 63), high=2 ** 63 - 1):
    if text == '-0' or re.fullmatch(r'-?(?:0|[1-9][0-9]*)', text) is None:
        raise Malformed('non-canonical integer ' + text)
    value = int(text)
    if not low <= value <= high:
        raise Malformed('integer out of range: ' + text)
    return value


def split_lines(raw):
    if not isinstance(raw, bytes):
        raise Malformed('input must be bytes')
    if not raw:
        raise Malformed('empty capture')
    if len(raw) > MAX_BYTES:
        raise Malformed('capture exceeds %d bytes' % MAX_BYTES)
    bad = [b for b in set(raw) if b != 0x0A and not 0x20 <= b <= 0x7E]
    if bad:
        raise Malformed('non-printable or non-ASCII byte 0x%02x (CR/TAB/NUL/UTF-8 not allowed)' % min(bad))
    if not raw.endswith(b'\n'):
        raise Malformed('final line lacks LF: capture truncated')
    lines = raw[:-1].split(b'\n')
    if len(lines) > MAX_LINES:
        raise Malformed('capture exceeds %d lines' % MAX_LINES)
    for line in lines:
        if len(line) > MAX_LINE_BYTES:
            raise Malformed('line exceeds %d bytes' % MAX_LINE_BYTES)
    return [line.decode('ascii') for line in lines]


def parse_framing(lines):
    """Return controller records [(seq, event, groups)] and {stream: [lines]}."""
    records, sections = [], {}
    index = 0
    if not lines or not lines[0].startswith('HXC1 seq=1 BEGIN '):
        raise Malformed('capture must start with HXC1 seq=1 BEGIN')
    while index < len(lines):
        line = lines[index]
        match = RECORD.fullmatch(line)
        if not match:
            raise Malformed('line %d outside a section is not an HXC1 record' % (index + 1))
        seq, event, rest = int(match.group(1)), match.group(2), match.group(3) or ''
        form = CONTROLLER.get(event)
        if form is None:
            raise Malformed('unknown controller event ' + event)
        fields = form.fullmatch(rest)
        if fields is None or (event == 'WATCHDOG_CANCELLED' and match.group(3) is not None):
            raise Malformed('malformed %s record at line %d' % (event, index + 1))
        if records and seq != records[-1][0] + 1:
            if seq <= records[-1][0]:
                raise Malformed('controller seq not increasing at line %d' % (index + 1))
            raise Malformed('controller seq gap: %d follows %d (record dropped or edited)' % (seq, records[-1][0]))
        records.append((seq, event, fields.groups()))
        index += 1
        if event == 'SECTION_BEGIN':
            stream, declared = fields.group(1), int(fields.group(2))
            if stream not in STREAMS:
                raise Malformed('unknown stream ' + stream)
            if stream in sections:
                raise Malformed('stream repeated: ' + stream)
            payload = []
            while index < len(lines) and not lines[index].startswith('HXC1 '):
                payload.append(lines[index])
                index += 1
            if sum(len(p) + 1 for p in payload) != declared:
                raise Malformed('stream %s byte count differs from declared %d' % (stream, declared))
            if index >= len(lines):
                raise Malformed('stream %s has no SECTION_END' % stream)
            end = RECORD.fullmatch(lines[index])
            if not end or end.group(2) != 'SECTION_END' or end.group(3) != 'stream=' + stream:
                raise Malformed('stream %s not closed by its SECTION_END' % stream)
            sections[stream] = payload
        elif event == 'SECTION_END' and (len(records) < 2 or records[-2][1] != 'SECTION_BEGIN'):
            raise Malformed('SECTION_END without SECTION_BEGIN')
    return records, sections


def event_key(event, groups):
    return event + ':' + groups[0] if event in ('SECTION_BEGIN', 'SECTION_END') else event


def check_controller(records, result):
    ids = {}
    keys = [event_key(event, groups) for _, event, groups in records]
    first = {}
    for position, (_, event, groups) in enumerate(records):
        first.setdefault(event, (position, groups))

    for _, event, groups in records:
        if event == 'ABORT':
            result.add('ABORTED', 'controller reported ABORT reason=' + groups[0])
        elif event == 'WATCHDOG_FIRED':
            result.add('TIMEOUT_OR_TERMINATED', 'controller watchdog fired, target=' + groups[0])
        elif event == 'END' and groups[0] != 'complete':
            result.add('ABORTED', 'controller END result=' + groups[0])

    for key in set(keys):
        if keys.count(key) > 1:
            result.add('CONTRADICTORY', 'controller record repeated: ' + key)
    for key in EXPECTED_EVENTS:
        if key not in keys:
            result.add('INCOMPLETE', 'missing controller record ' + key)
    if keys and keys[-1] != 'END':
        result.add('INCOMPLETE', 'capture does not end with an END record')
    present = [k for k in keys if k in EXPECTED_EVENTS]
    expected_present = [k for k in EXPECTED_EVENTS if k in keys]
    if present != expected_present:
        result.add('CONTRADICTORY', 'controller records out of the required order')

    # Release gating (requirement 3). Checked by position so it survives reordering.
    if 'RELEASE_SENT' in first:
        release = first['RELEASE_SENT'][0]
        for needed in ('HELD_OBSERVED', 'PROVIDER_REAPED', 'ENDPOINT_ABSENT', 'CONTROL_TRACE_OK'):
            if needed not in first or first[needed][0] > release:
                result.add('PREREQUISITE_FAILED', 'premature release: RELEASE_SENT before ' + needed)

    if 'BEGIN' not in first:
        return ids
    contract, controller, cpid, pbin, rbin, fixture = first['BEGIN'][1]
    if contract != CONTRACT:
        raise Malformed('unsupported contract ' + contract)
    if controller != CONTROLLER_REVISION:
        result.add('PREREQUISITE_FAILED', 'unreviewed controller revision ' + controller)
    if pbin != PROVIDER_BIN or rbin != READER_BIN:
        result.add('PREREQUISITE_FAILED', 'provider/reader binary names differ from the reviewed pins')
    ids['controller'] = number(cpid, 2, 2 ** 31 - 1)
    c = ids['controller']
    if fixture != '/ramdisk/mm/.nbt-held-alias-586.%d' % c:
        result.add('CONTRADICTORY', 'fixture path does not match controller PID')
    if 'PROVIDER_STARTED' in first:
        ids['provider'] = number(first['PROVIDER_STARTED'][1][0], 2, 2 ** 31 - 1)
    if 'READER_STARTED' in first:
        rpid, parent, provider = first['READER_STARTED'][1]
        ids['reader'] = number(rpid, 2, 2 ** 31 - 1)
        if number(parent) != c:
            result.add('CONTRADICTORY', 'READER_STARTED parent is not the controller')
        if 'provider' in ids and number(provider) != ids['provider']:
            result.add('CONTRADICTORY', 'READER_STARTED provider differs from PROVIDER_STARTED')
    p, r = ids.get('provider'), ids.get('reader')
    if len({c, p, r} - {None}) != len([v for v in (c, p, r) if v is not None]):
        result.add('CONTRADICTORY', 'controller, provider and reader PIDs are not distinct')
    endpoint = '/dev/nbt_large_endpoint_586.%s' % p
    for _, event, groups in records:
        if event == 'PROVIDER_READY' and (number(groups[0]) != p or groups[1] != endpoint):
            result.add('CONTRADICTORY', 'PROVIDER_READY identity mismatch')
        elif event == 'ALIAS_CREATED' and (groups[0] != fixture + '/dummy-body.bin' or groups[1] != endpoint):
            result.add('CONTRADICTORY', 'ALIAS_CREATED path/target mismatch')
        elif event == 'HELD_OBSERVED' and number(groups[0]) != r:
            result.add('CONTRADICTORY', 'HELD_OBSERVED reader identity mismatch')
        elif event == 'PROVIDER_REAPED':
            if number(groups[0]) != p:
                result.add('CONTRADICTORY', 'PROVIDER_REAPED is not the started provider')
            status = number(groups[1], 0, 255)
            ids['provider_status'] = status
            if status != 0:
                result.add('PREREQUISITE_FAILED', 'provider did not exit normally: ' + describe_status(status))
        elif event == 'ENDPOINT_ABSENT' and groups[0] != endpoint:
            result.add('CONTRADICTORY', 'ENDPOINT_ABSENT names a different endpoint')
        elif event == 'CONTROL_TRACE_OK' and number(groups[0]) != p:
            result.add('CONTRADICTORY', 'CONTROL_TRACE_OK names a different provider')
        elif event == 'RELEASE_SENT' and number(groups[0]) != r:
            result.add('CONTRADICTORY', 'release sent to a process other than the reader')
        elif event == 'READER_REAPED':
            if number(groups[0]) != r:
                result.add('CONTRADICTORY', 'READER_REAPED is not the started reader')
            ids['reader_status'] = number(groups[1], 0, 255)
        elif event == 'FIXTURE_CLEANED' and groups[0] != fixture:
            result.add('CONTRADICTORY', 'FIXTURE_CLEANED names a different fixture')
    return ids


def describe_status(status):
    if status > 128:
        signal = status - 128
        return 'status %d (signal %d %s, assuming shell 128+n)' % (status, signal, SIGNAL_NAMES.get(signal, '?'))
    return 'status %d' % status


def check_provider(lines, errors, ids, result):
    out = {'elapsed_ms': None, 'events': None, 'trace': []}
    if errors:
        result.add('PREREQUISITE_FAILED', 'provider stderr is not empty (%d lines)' % len(errors))
    if lines is None:
        return out
    p = ids.get('provider')
    expected_kinds = ['READY', 'TRACE_SUMMARY', 'TRACE_READ', 'TRACE_SEEK', 'DETACHED']
    kinds = []
    for line in lines:
        match = P_READY.fullmatch(line)
        if match:
            kinds.append('READY')
            pid, path_pid, size, lease = map(number, match.groups())
            if pid != p or path_pid != p:
                result.add('CONTRADICTORY', 'provider READY identity differs from PROVIDER_STARTED')
            if size != BODY_BYTES or lease != LEASE_MS:
                result.add('PREREQUISITE_FAILED', 'provider READY reports a different body or lease')
            continue
        match = P_SUMMARY.fullmatch(line)
        if match:
            kinds.append('TRACE_SUMMARY')
            events, dropped, overflow, elapsed = map(number, match.groups())
            out['events'], out['elapsed_ms'] = events, elapsed
            if dropped or overflow:
                result.add('INCOMPLETE', 'provider trace overflowed (dropped=%d)' % dropped)
            if events > 2:
                result.add('CONTRADICTORY', 'provider served %d requests; only the two controls are allowed' % events)
            elif events < 2:
                result.add('PREREQUISITE_FAILED', 'provider trace lacks the two control requests')
            if elapsed < LEASE_MS:
                result.add('CONTRADICTORY', 'deadline exit with elapsed_ms below the 10000 ms lease')
            continue
        match = P_READ.fullmatch(line)
        if match:
            kinds.append('TRACE_READ')
            index, before, requested, xtype, count, after, rc = map(number, match.groups())
            out['trace'].append({'index': index, 'kind': 'read', 'before': before, 'requested': requested,
                                 'xtype': xtype, 'count': count, 'after': after, 'endpoint_reply_code': rc})
            if (index, before, xtype, count, after) != (0, 0, 0, 100, 100) or requested != 100:
                result.add('PREREQUISITE_FAILED', 'control read trace is not index=0 0->100 requested=100 count=100'
                           ' (requested=%d: buffering or wrong client?)' % requested)
            if rc != -1:
                result.add('PREREQUISITE_FAILED', 'control read reply code %d is not the reviewed -1' % rc)
            continue
        match = P_SEEK.fullmatch(line)
        if match:
            kinds.append('TRACE_SEEK')
            index, before, bits, whence, after, rc = match.groups()
            index, before, whence, after, rc = map(number, (index, before, whence, after, rc))
            out['trace'].append({'index': index, 'kind': 'seek', 'before': before, 'offset_bits': bits,
                                 'whence': whence, 'after': after, 'endpoint_reply_code': rc})
            if (index, before, bits, whence, after) != (1, 100, '0' * 16, 1, 100):
                result.add('PREREQUISITE_FAILED', 'control seek trace is not index=1 SEEK_CUR(1) at offset 100')
            if rc != -1:
                result.add('PREREQUISITE_FAILED', 'control seek reply code %d is not the reviewed -1' % rc)
            continue
        match = P_DETACHED.fullmatch(line)
        if match:
            kinds.append('DETACHED')
            if match.group(1) != 'deadline':
                result.add('PREREQUISITE_FAILED', 'provider detached for reason=' + match.group(1))
            continue
        if line.startswith('STOP:'):
            result.add('PREREQUISITE_FAILED', 'provider reported: ' + line)
            kinds.append('STOP')
            continue
        raise Malformed('unknown provider stdout line')
    if kinds != expected_kinds:
        missing = [k for k in expected_kinds if k not in kinds]
        if missing:
            result.add('INCOMPLETE', 'provider stdout lacks ' + ', '.join(missing))
        if len(kinds) != len(set(kinds)) or [k for k in kinds if k in expected_kinds] != \
                [k for k in expected_kinds if k in kinds]:
            result.add('CONTRADICTORY', 'provider stdout records repeated or out of order')
        if 'DETACHED' not in kinds and ids.get('provider_status') == 0:
            result.add('CONTRADICTORY', 'provider exit status 0 without its DETACHED line')
    return out


def parse_reader(lines):
    records = []
    for line in lines:
        for kind, form in R_FORMS:
            match = form.fullmatch(line)
            if match:
                records.append((kind, match.groups(), line))
                break
        else:
            raise Malformed('unknown reader stdout line')
    return records


def check_errno(name, rc, err, result):
    # Actual reviewed QNX SDK: ssize_t, off_t and errno are signed 32-bit.
    if not -(2 ** 31) <= rc < 2 ** 31 or not -(2 ** 31) <= err < 2 ** 31:
        raise Malformed('%s result/errno exceeds captured signed 32-bit SDK type' % name)
    if rc == -1 and err < 1:
        result.add('CONTRADICTORY', '%s reports rc=-1 with errno=%d' % (name, err))
        return False
    if rc != -1 and err != 0:
        result.add('CONTRADICTORY', '%s reports rc=%d with errno=%d' % (name, rc, err))
        return False
    return True


def check_reader_record(position, record, ids, result, out):
    kind, groups, _ = record
    if kind == 'CONTROL_END':
        name, rc, err = groups[0], number(groups[1]), number(groups[2])
        if not check_errno('control ' + name, rc, err, result):
            return False
        if rc != 100:
            result.add('PREREQUISITE_FAILED', 'control %s returned rc=%d errno=%d' % (name, rc, err))
            return False
    elif kind == 'HELD':
        pid, parent, provider = map(number, groups)
        if (pid, parent, provider) != (ids.get('reader'), ids.get('controller'), ids.get('provider')):
            result.add('CONTRADICTORY', 'reader HELD identities differ from controller records')
            return False
    elif kind == 'RELEASED':
        if number(groups[0]) != ids.get('controller'):
            result.add('CONTRADICTORY', 'reader released by a sender other than the controller')
            return False
    elif kind == 'OP_END':
        name, rc, err, elapsed = groups[0], number(groups[1]), number(groups[2]), number(groups[3])
        entry = {'name': name, 'syscall_result': rc, 'errno': err if rc == -1 else None, 'elapsed_ms': elapsed}
        if name == 'close':
            out['close'] = entry
        else:
            out['probes'].append(entry)
        if elapsed < 0:
            result.add('CONTRADICTORY', '%s has negative elapsed_ms' % name)
            return False
        if not check_errno(name, rc, err, result):
            return False
        if elapsed >= PROBE_BOUND_MS:
            result.add('TIMEOUT_OR_TERMINATED', '%s took %d ms (bound %d)' % (name, elapsed, PROBE_BOUND_MS))
            return False
        if name == 'close':
            if rc not in (0, -1):
                result.add('CONTRADICTORY', 'close returned %d' % rc)
                return False
        elif rc != -1:
            if name == 'seek_start':
                detail = 'seek succeeded, returned offset %d' % rc
            elif rc == 0:
                detail = 'zero-byte read at offset 100 (not legitimate EOF)'
            elif 0 < rc <= 64:
                detail = 'read returned %d bytes' % rc
            else:
                result.add('CONTRADICTORY', '%s returned impossible rc=%d' % (name, rc))
                return False
            result.add('UNEXPECTED_PROBE_RESULT', '%s: %s after provider exit' % (name, detail))
            return False
    return True


def check_reader(lines, errors, ids, result):
    out = {'probes': [], 'close': None, 'last_record': None}
    if errors:
        result.add('PREREQUISITE_FAILED', 'reader stderr is not empty (%d lines)' % len(errors))
    if lines is None:
        return out
    records = parse_reader(lines)
    kinds = [k for k, _, _ in records]
    status = ids.get('reader_status')
    out['last_record'] = records[-1][2] if records else None
    if kinds.count('OBSERVED') + kinds.count('STOP') > 1:
        result.add('CONTRADICTORY', 'reader emitted more than one final marker')
    if 'OBSERVED' in kinds and status not in (None, 0):
        result.add('CONTRADICTORY', 'reader OBSERVED but exited ' + describe_status(status))
    if 'STOP' in kinds and status == 0:
        result.add('CONTRADICTORY', 'reader STOP but exited 0')
    if status not in (None, 0) and status > 128:
        result.add('TIMEOUT_OR_TERMINATED', 'reader terminated, %s; last record: %s'
                   % (describe_status(status), out['last_record']))
    elif status not in (None, 0):
        result.add('INCOMPLETE', 'reader exited ' + describe_status(status))
    if status == 0 and 'OBSERVED' not in kinds:
        result.add('CONTRADICTORY', 'reader exited 0 without its OBSERVED marker')

    for position, want in enumerate(R_TEMPLATE):
        if position >= len(records):
            if status is not None and status <= 128:
                result.add('INCOMPLETE', 'reader stream ends before %s %s' % want)
            return out
        kind, groups, line = records[position]
        name = groups[0] if groups else None
        if (kind, name if want[1] else None) != want:
            if kind == 'STOP':
                category = 'PREREQUISITE_FAILED' if position <= 5 else 'INCOMPLETE'
                result.add(category, 'reader stopped where %s %s was expected' % want)
            elif kind == 'OP_BEGIN' and groups[0] == 'close' and position > 5:
                result.add('INCOMPLETE', 'reader skipped to close where %s %s was expected' % want)
            else:
                result.add('CONTRADICTORY', 'reader record out of order: %s' % line)
            if 'OBSERVED' in kinds[position:]:
                result.add('CONTRADICTORY', 'reader OBSERVED after a deviation')
            return out
        if not check_reader_record(position, records[position], ids, result, out):
            if 'OBSERVED' in kinds[position + 1:]:
                result.add('CONTRADICTORY', 'reader OBSERVED despite a failed check')
            return out
    if len(records) > len(R_TEMPLATE):
        result.add('CONTRADICTORY', 'reader records after OBSERVED')
    return out


def assess(raw):
    result = Assessment()
    report = {'contract': CONTRACT, 'contract_status': 'PROPOSED', 'proposal_revision': PROPOSAL_REVISION, 'input_authenticated': False}
    try:
        lines = split_lines(raw)
        records, sections = parse_framing(lines)
        ids = check_controller(records, result)
        report['identities'] = {k: ids[k] for k in ('controller', 'provider', 'reader') if k in ids}
        report['provider'] = check_provider(sections.get('provider.stdout'),
                                            sections.get('provider.stderr'), ids, result)
        report['reader'] = check_reader(sections.get('reader.stdout'),
                                        sections.get('reader.stderr'), ids, result)
        report['reader']['exit_status'] = ids.get('reader_status')
        report['provider']['exit_status'] = ids.get('provider_status')
    except Malformed as error:
        result.add('MALFORMED', str(error))
    report['verdict'] = result.verdict()
    report['findings'] = result.findings
    report['notes'] = ['TRACE rc values are provider resource-manager reply codes; reader rc values are syscall results.',
                       'errno values are recorded, not required to equal any particular value.',
                       'A PASS describes this capture only; it is not a general QNX result.']
    report.update({'hmi_integration_verified': False, 'plugin_execution_verified': False,
                   'live_rpm_verified': False})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='captured controller log for exactly one trial')
    args = parser.parse_args(argv)
    if args.input is None:
        parser.print_help()
        return 0
    try:
        with args.input.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        print('STOP: cannot read input: ' + str(error), file=sys.stderr)
        return 1
    report = assess(raw)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report['verdict'] == 'PASS':
        print('PASS: held-expiry-log/1 capture satisfies every assessed requirement')
        return 0
    print('STOP: %s' % report['verdict'], file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
