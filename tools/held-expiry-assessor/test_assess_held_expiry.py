#!/usr/bin/env python3
"""Tests on SYNTHETIC logs only. No log here came from QNX, the BMW or a controller.

PIDs 11111/22222/33333 and every errno value are invented. Passing these tests
says nothing about native behaviour, HMI, plugins or live RPM.
"""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import assess_held_expiry as A

HERE = Path(__file__).resolve().parent
C, P, R = 11111, 22222, 33333
FIXTURE = '/ramdisk/mm/.nbt-held-alias-586.%d' % C
ENDPOINT = '/dev/nbt_large_endpoint_586.%d' % P


def provider_lines(elapsed=10021):
    return ['READY pid=%d path=%s bytes=586 lease_ms=10000' % (P, ENDPOINT),
            'TRACE_SUMMARY events=2 dropped=0 overflow=0 elapsed_ms=%d' % elapsed,
            'TRACE_READ index=0 before=0 requested=100 xtype=0 count=100 after=100 rc=-1',
            'TRACE_SEEK index=1 before=100 offset_bits=0000000000000000 whence=1 after=100 rc=-1',
            'DETACHED reason=deadline; endpoint server exiting']


def reader_lines(errnos=(9, 9, 9), close='rc=0 errno=0'):
    lines = ['CONTROL_BEGIN name=read100', 'CONTROL_END name=read100 rc=100 errno=0',
             'CONTROL_BEGIN name=seek_current', 'CONTROL_END name=seek_current rc=100 errno=0',
             'HELD pid=%d parent=%d provider=%d offset=100' % (R, C, P), 'RELEASED sender=%d' % C]
    for name, err in zip(A.PROBES, errnos):
        lines += ['OP_BEGIN name=' + name, 'OP_END name=%s rc=-1 errno=%d elapsed_ms=1' % (name, err)]
    lines += ['OP_BEGIN name=close', 'OP_END name=close %s elapsed_ms=0' % close, A.OBSERVED]
    return lines


def events(provider=None, reader=None, provider_err=(), reader_err=(),
           provider_status=0, reader_status=0):
    return ['BEGIN contract=held-expiry-log/1 controller=held-controller-1 controller_pid=%d '
            'provider_bin=%s reader_bin=%s fixture=%s' % (C, A.PROVIDER_BIN, A.READER_BIN, FIXTURE),
            'PROVIDER_STARTED pid=%d' % P,
            'PROVIDER_READY pid=%d path=%s' % (P, ENDPOINT),
            'ALIAS_CREATED path=%s/dummy-body.bin target=%s' % (FIXTURE, ENDPOINT),
            'READER_STARTED pid=%d parent=%d provider=%d' % (R, C, P),
            'HELD_OBSERVED reader=%d' % R,
            'PROVIDER_REAPED pid=%d status=%d' % (P, provider_status),
            'ENDPOINT_ABSENT path=%s alias=dangling' % ENDPOINT,
            'CONTROL_TRACE_OK provider=%d events=2' % P,
            'RELEASE_SENT reader=%d signal=USR1' % R,
            'READER_REAPED pid=%d status=%d' % (R, reader_status),
            ('provider.stdout', provider_lines() if provider is None else provider),
            ('provider.stderr', list(provider_err)),
            ('reader.stdout', reader_lines() if reader is None else reader),
            ('reader.stderr', list(reader_err)),
            'FIXTURE_CLEANED path=' + FIXTURE,
            'WATCHDOG_CANCELLED',
            'END result=complete']


def build(items):
    """Render events with correct seq numbers and byte counts."""
    out, seq = [], 0
    for item in items:
        if isinstance(item, tuple):
            stream, payload = item
            seq += 1
            out.append('HXC1 seq=%d SECTION_BEGIN stream=%s bytes=%d'
                       % (seq, stream, sum(len(p) + 1 for p in payload)))
            out += payload
            seq += 1
            out.append('HXC1 seq=%d SECTION_END stream=%s' % (seq, stream))
        else:
            seq += 1
            out.append('HXC1 seq=%d %s' % (seq, item))
    return ('\n'.join(out) + '\n').encode('ascii')


VALID = build(events())


def verdict(raw):
    return A.assess(raw)['verdict']


def replace_event(items, prefix, new):
    hits = [i for i, e in enumerate(items) if isinstance(e, str) and e.startswith(prefix)]
    assert len(hits) == 1, prefix
    items[hits[0]] = new
    return items


class Valid(unittest.TestCase):
    def test_synthetic_complete_trial_passes(self):
        report = A.assess(VALID)
        self.assertEqual(report['verdict'], 'PASS', report['findings'])
        self.assertEqual(report['identities'], {'controller': C, 'provider': P, 'reader': R})
        self.assertEqual([p['syscall_result'] for p in report['reader']['probes']], [-1, -1, -1])
        self.assertEqual({t['endpoint_reply_code'] for t in report['provider']['trace']}, {-1})
        self.assertFalse(report['live_rpm_verified'])
        self.assertFalse(report['input_authenticated'])

    def test_errno_values_are_recorded_not_assumed(self):
        for errnos in [(9, 9, 9), (3, 3, 3), (6, 89, 9), (1, 2, 3)]:
            report = A.assess(build(events(reader=reader_lines(errnos))))
            self.assertEqual(report['verdict'], 'PASS', errnos)
            self.assertEqual(tuple(p['errno'] for p in report['reader']['probes']), errnos)

    def test_failed_close_is_observational(self):
        report = A.assess(build(events(reader=reader_lines(close='rc=-1 errno=9'))))
        self.assertEqual(report['verdict'], 'PASS')
        self.assertEqual(report['reader']['close']['errno'], 9)

    def test_provider_elapsed_reported_not_bounded_above(self):
        report = A.assess(build(events(provider=provider_lines(elapsed=14000))))
        self.assertEqual((report['verdict'], report['provider']['elapsed_ms']), ('PASS', 14000))


class Requirement1Controls(unittest.TestCase):
    def check(self, old, new, category):
        """Model the real reader: a failed check goes to done, prints STOP, exits 1."""
        base = reader_lines()
        at = base.index(old)
        lines = base[:at] + [new, A.STOP]
        self.assertEqual(verdict(build(events(reader=lines, reader_status=1))), category)

    def check_line(self, old, new, category):
        lines = [new if line == old else line for line in reader_lines()]
        self.assertNotEqual(lines, reader_lines())
        self.assertEqual(verdict(build(events(reader=lines))), category)

    def test_forged_continuation_after_failed_control_is_contradictory(self):
        lines = [l.replace('read100 rc=100', 'read100 rc=99') for l in reader_lines()]
        self.assertEqual(verdict(build(events(reader=lines))), 'CONTRADICTORY')

    def test_failed_controls_refused(self):
        self.check('CONTROL_END name=read100 rc=100 errno=0', 'CONTROL_END name=read100 rc=99 errno=0',
                   'PREREQUISITE_FAILED')
        self.check('CONTROL_END name=seek_current rc=100 errno=0',
                   'CONTROL_END name=seek_current rc=-1 errno=22', 'PREREQUISITE_FAILED')

    def test_reader_stop_before_held_refused(self):
        lines = reader_lines()[:2] + [A.STOP]
        self.assertEqual(verdict(build(events(reader=lines, reader_status=1))), 'PREREQUISITE_FAILED')

    def test_incomplete_held_line_refused(self):
        self.check_line('HELD pid=%d parent=%d provider=%d offset=100' % (R, C, P),
                   'HELD pid=%d parent=%d provider=%d offset=10' % (R, C, P), 'MALFORMED')


class Requirement2Trace(unittest.TestCase):
    def check(self, old, new, category):
        lines = [line.replace(old, new) for line in provider_lines()]
        self.assertNotEqual(lines, provider_lines())
        self.assertEqual(verdict(build(events(provider=lines))), category)

    def test_buffered_or_wrong_control_read_refused(self):
        self.check('requested=100', 'requested=1024', 'PREREQUISITE_FAILED')
        self.check('count=100 after=100', 'count=99 after=99', 'PREREQUISITE_FAILED')

    def test_wrong_control_seek_refused(self):
        self.check('whence=1', 'whence=0', 'PREREQUISITE_FAILED')
        self.check('before=100 offset_bits', 'before=0 offset_bits', 'PREREQUISITE_FAILED')
        self.check('offset_bits=0000000000000000', 'offset_bits=0000000000000001', 'PREREQUISITE_FAILED')

    def test_reply_code_must_be_reviewed_value(self):
        self.check('whence=1 after=100 rc=-1', 'whence=1 after=100 rc=22', 'PREREQUISITE_FAILED')
        self.check('count=100 after=100 rc=-1', 'count=100 after=100 rc=0', 'PREREQUISITE_FAILED')

    def test_overflow_or_missing_events_refused(self):
        self.check('dropped=0', 'dropped=1', 'INCOMPLETE')
        lines = [l for l in provider_lines() if not l.startswith('TRACE_SEEK')]
        self.assertNotEqual(verdict(build(events(provider=lines))), 'PASS')

    def test_extra_provider_request_is_contradictory(self):
        lines = provider_lines()
        lines[1] = lines[1].replace('events=2', 'events=3')
        lines.insert(4, 'TRACE_READ index=2 before=100 requested=64 xtype=0 count=64 after=164 rc=-1')
        self.assertEqual(verdict(build(events(provider=lines))), 'CONTRADICTORY')

    def test_elapsed_below_lease_is_contradictory(self):
        self.assertEqual(verdict(build(events(provider=provider_lines(elapsed=9999)))), 'CONTRADICTORY')


class Requirement3Release(unittest.TestCase):
    def move_release_before(self, target):
        items = events()
        release = next(e for e in items if isinstance(e, str) and e.startswith('RELEASE_SENT'))
        items.remove(release)
        index = next(i for i, e in enumerate(items) if isinstance(e, str) and e.startswith(target))
        items.insert(index, release)
        return A.assess(build(items))

    def test_premature_release_never_passes(self):
        for target in ('HELD_OBSERVED', 'PROVIDER_REAPED', 'ENDPOINT_ABSENT', 'CONTROL_TRACE_OK'):
            report = self.move_release_before(target)
            self.assertNotEqual(report['verdict'], 'PASS', target)
            self.assertTrue(any('premature release' in f['message'] for f in report['findings']), target)

    def test_abnormal_provider_exit_refused(self):
        for status in (1, 2, 137):
            self.assertEqual(verdict(build(events(provider_status=status))), 'PREREQUISITE_FAILED')
        lines = [l.replace('reason=deadline', 'reason=signal') for l in provider_lines()]
        self.assertEqual(verdict(build(events(provider=lines))), 'PREREQUISITE_FAILED')

    def test_missing_endpoint_absence_refused(self):
        items = [e for e in events() if not (isinstance(e, str) and e.startswith('ENDPOINT_ABSENT'))]
        self.assertNotEqual(verdict(build(items)), 'PASS')

    def test_status_zero_without_detached_is_contradictory(self):
        lines = [l for l in provider_lines() if not l.startswith('DETACHED')]
        self.assertEqual(verdict(build(events(provider=lines))), 'CONTRADICTORY')


class Requirement4Identity(unittest.TestCase):
    def test_identity_mismatches_refused(self):
        cases = [('READER_STARTED', 'READER_STARTED pid=%d parent=44444 provider=%d' % (R, P)),
                 ('HELD_OBSERVED', 'HELD_OBSERVED reader=44444'),
                 ('PROVIDER_READY', 'PROVIDER_READY pid=44444 path=%s' % ENDPOINT),
                 ('ALIAS_CREATED', 'ALIAS_CREATED path=%s/dummy-body.bin target=/dev/nbt_large_endpoint_586.44444' % FIXTURE),
                 ('PROVIDER_REAPED', 'PROVIDER_REAPED pid=44444 status=0'),
                 ('RELEASE_SENT', 'RELEASE_SENT reader=44444 signal=USR1'),
                 ('READER_REAPED', 'READER_REAPED pid=44444 status=0'),
                 ('FIXTURE_CLEANED', 'FIXTURE_CLEANED path=/ramdisk/mm/.nbt-held-alias-586.44444')]
        for prefix, new in cases:
            self.assertEqual(verdict(build(replace_event(events(), prefix, new))), 'CONTRADICTORY', prefix)

    def test_reader_stream_identity_mismatches_refused(self):
        for old, new in [('parent=%d' % C, 'parent=44444'), ('provider=%d offset' % P, 'provider=44444 offset'),
                         ('sender=%d' % C, 'sender=44444')]:
            lines = [l.replace(old, new) for l in reader_lines()]
            self.assertEqual(verdict(build(events(reader=lines))), 'CONTRADICTORY', old)

    def test_shared_pids_refused(self):
        items = replace_event(events(), 'READER_STARTED', 'READER_STARTED pid=%d parent=%d provider=%d' % (P, C, P))
        self.assertNotEqual(verdict(build(items)), 'PASS')

    def test_unreviewed_binary_names_refused(self):
        items = events()
        items[0] = items[0].replace(A.READER_BIN, '/dev/shmem/nbt_hold_reader_586_000000000000')
        self.assertEqual(verdict(build(items)), 'PREREQUISITE_FAILED')


class Requirement5Probes(unittest.TestCase):
    def anomaly(self, name, rc, err=0):
        lines = reader_lines()
        at = lines.index('OP_END name=%s rc=-1 errno=9 elapsed_ms=1' % name)
        lines = lines[:at] + ['OP_END name=%s rc=%d errno=%d elapsed_ms=1' % (name, rc, err),
                              'OP_BEGIN name=close', 'OP_END name=close rc=0 errno=0 elapsed_ms=0', A.STOP]
        return A.assess(build(events(reader=lines, reader_status=1)))

    def test_zero_byte_read_is_unexpected_not_eof(self):
        report = self.anomaly('read64_a', 0)
        self.assertEqual(report['verdict'], 'UNEXPECTED_PROBE_RESULT')
        self.assertTrue(any('zero-byte' in f['message'] for f in report['findings']))

    def test_successful_read_and_seek_are_unexpected(self):
        self.assertEqual(self.anomaly('read64_b', 64)['verdict'], 'UNEXPECTED_PROBE_RESULT')
        self.assertEqual(self.anomaly('seek_start', 0)['verdict'], 'UNEXPECTED_PROBE_RESULT')

    def test_forged_observed_after_success_is_contradictory(self):
        lines = [l.replace('name=read64_a rc=-1 errno=9', 'name=read64_a rc=64 errno=0') for l in reader_lines()]
        self.assertEqual(verdict(build(events(reader=lines))), 'CONTRADICTORY')

    def test_probe_bound_and_kill_are_timeouts(self):
        lines = [l.replace('name=seek_start rc=-1 errno=9 elapsed_ms=1', 'name=seek_start rc=-1 errno=9 elapsed_ms=3000')
                 for l in reader_lines()]
        self.assertEqual(verdict(build(events(reader=lines))), 'CONTRADICTORY')  # OBSERVED despite reader's own bound
        killed = reader_lines()[:reader_lines().index('OP_BEGIN name=read64_b') + 1]
        report = A.assess(build(events(reader=killed, reader_status=142)))
        self.assertEqual(report['verdict'], 'TIMEOUT_OR_TERMINATED')
        self.assertIn('OP_BEGIN name=read64_b', report['reader']['last_record'])

    def test_over_bound_with_reader_stop_is_timeout(self):
        lines = reader_lines()[:reader_lines().index('OP_BEGIN name=read64_b')]
        lines[-1] = 'OP_END name=seek_start rc=-1 errno=9 elapsed_ms=3000'
        lines += ['OP_BEGIN name=close', 'OP_END name=close rc=0 errno=0 elapsed_ms=0', A.STOP]
        self.assertEqual(verdict(build(events(reader=lines, reader_status=1))), 'TIMEOUT_OR_TERMINATED')

    def test_errno_inconsistent_with_result_is_contradictory(self):
        for old, new in [('rc=-1 errno=9 elapsed_ms=1', 'rc=-1 errno=0 elapsed_ms=1'),
                         ('close rc=0 errno=0', 'close rc=0 errno=9')]:
            lines = [l.replace(old, new, 1) for l in reader_lines()]
            self.assertEqual(verdict(build(events(reader=lines))), 'CONTRADICTORY', old)


class Requirement6Completion(unittest.TestCase):
    def test_missing_close_or_cleanup_refused(self):
        lines = [l for l in reader_lines() if 'name=close' not in l]
        self.assertNotEqual(verdict(build(events(reader=lines))), 'PASS')
        items = [e for e in events() if not (isinstance(e, str) and e.startswith('FIXTURE_CLEANED'))]
        self.assertEqual(verdict(build(items)), 'INCOMPLETE')

    def test_reader_exit_status_must_be_zero(self):
        self.assertEqual(verdict(build(events(reader_status=1))), 'CONTRADICTORY')

    def test_reader_exit_zero_alone_is_insufficient(self):
        bare = ('\n'.join(reader_lines()) + '\nREADER_EXIT 0\n').encode()
        self.assertEqual(verdict(bare), 'MALFORMED')
        items = [e for e in events() if not (isinstance(e, tuple) and e[0].startswith('provider'))]
        self.assertNotEqual(verdict(build(items)), 'PASS')

    def test_stderr_diagnostics_refused(self):
        self.assertEqual(verdict(build(events(reader_err=['ldqnx: diagnostic']))), 'PREREQUISITE_FAILED')
        self.assertEqual(verdict(build(events(provider_err=['dispatch_block/receive: error']))),
                         'PREREQUISITE_FAILED')


class Requirement7Integrity(unittest.TestCase):
    def test_controller_failure_records_refused(self):
        for item, category in [('WATCHDOG_FIRED target=reader', 'TIMEOUT_OR_TERMINATED'),
                               ('ABORT reason=held_not_observed', 'ABORTED')]:
            items = events()
            items.insert(-1, item)
            self.assertNotEqual(verdict(build(items)), 'PASS', item)
            self.assertIn(category, [f['category'] for f in A.assess(build(items))['findings']])
        items = events()
        items[-1] = 'END result=aborted'
        self.assertEqual(verdict(build(items)), 'ABORTED')

    def test_framing_corruption_is_malformed(self):
        text = VALID.decode()
        cases = [text.replace('seq=5 ', 'seq=6 ', 1),                     # gap/duplicate
                 text.replace('seq=3 ', 'seq=30 ', 1),                    # gap
                 text.replace('bytes=', 'bytes=1', 1),                    # byte count
                 text.replace('WATCHDOG_CANCELLED', 'WATCHDOG_CANCELED'),  # unknown event
                 text.replace('held-expiry-log/1', 'held-expiry-log/2'),   # version
                 text.replace('pid=%d\n' % P, 'pid=0%d\n' % P, 1),         # leading zero
                 'preamble from transport\n' + text,
                 text.replace('READY pid', 'HXC1 READY pid'),
                 text.replace('\n', '\r\n'),
                 text.replace('RELEASED', 'RELEASED\x00'),
                 text[:-1],
                 text.replace('DETACHED', 'DETACHÉD'),
                 text.replace('OP_BEGIN name=close', 'OP_BEGIN name=close' + ' ' * 600)]
        for case in cases:
            self.assertEqual(verdict(case.encode('utf-8')), 'MALFORMED', case[:80])

    def test_oversized_inputs_are_bounded(self):
        self.assertEqual(verdict(b''), 'MALFORMED')
        self.assertEqual(verdict(b'x' * (A.MAX_BYTES + 1)), 'MALFORMED')
        self.assertEqual(verdict(b'\n' * (A.MAX_LINES + 1)), 'MALFORMED')

    def test_huge_integers_do_not_crash(self):
        text = VALID.decode().replace('elapsed_ms=10021', 'elapsed_ms=' + '9' * 19)
        self.assertEqual(verdict(text.encode()), 'MALFORMED')

    def test_repeated_section_is_malformed(self):
        items = events()
        items.insert(-2, ('reader.stderr', []))
        self.assertEqual(verdict(build(items)), 'MALFORMED')


class MutationSweeps(unittest.TestCase):
    """No single deletion, duplication, swap or truncation of a valid log may PASS."""

    def test_every_line_prefix_fails(self):
        lines = VALID.decode().splitlines()
        for n in range(len(lines)):
            raw = ('\n'.join(lines[:n]) + '\n').encode() if n else b''
            self.assertNotEqual(verdict(raw), 'PASS', n)

    def test_every_byte_truncation_fails(self):
        for n in range(len(VALID)):
            self.assertNotEqual(verdict(VALID[:n]), 'PASS', n)

    def test_semantic_deletion_with_rebuilt_framing_fails(self):
        base = events()
        for i, item in enumerate(base):
            if isinstance(item, str):
                self.assertNotEqual(verdict(build(base[:i] + base[i + 1:])), 'PASS', item)
                continue
            for j in range(len(item[1])):
                trimmed = base[:i] + [(item[0], item[1][:j] + item[1][j + 1:])] + base[i + 1:]
                self.assertNotEqual(verdict(build(trimmed)), 'PASS', item[1][j])

    def test_semantic_duplication_and_swap_with_rebuilt_framing_fails(self):
        base = events()
        for i, item in enumerate(base):
            if isinstance(item, str):
                self.assertNotEqual(verdict(build(base[:i + 1] + [item] + base[i + 1:])), 'PASS', item)
                if i + 1 < len(base):
                    swapped = base[:i] + [base[i + 1], item] + base[i + 2:]
                    self.assertNotEqual(verdict(build(swapped)), 'PASS', item)
                continue
            payload = item[1]
            for j in range(len(payload)):
                dup = payload[:j + 1] + [payload[j]] + payload[j + 1:]
                self.assertNotEqual(verdict(build(base[:i] + [(item[0], dup)] + base[i + 1:])), 'PASS')
                if j + 1 < len(payload):
                    sw = payload[:j] + [payload[j + 1], payload[j]] + payload[j + 2:]
                    self.assertNotEqual(verdict(build(base[:i] + [(item[0], sw)] + base[i + 1:])), 'PASS',
                                        payload[j])


class Robustness(unittest.TestCase):
    def test_random_byte_mutations_never_crash(self):
        import random
        rng = random.Random(20261126)
        allowed = {'PASS'} | set(A.PRECEDENCE)
        for _ in range(3000):
            raw = bytearray(VALID)
            for _ in range(rng.randint(1, 4)):
                raw[rng.randrange(len(raw))] = rng.randrange(256)
            report = A.assess(bytes(raw))
            self.assertIn(report['verdict'], allowed)
            if any(b != 0x0A and not 0x20 <= b <= 0x7E for b in raw):
                self.assertEqual(report['verdict'], 'MALFORMED')


class CommandLine(unittest.TestCase):
    SCRIPT = str(HERE / 'assess_held_expiry.py')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', self.SCRIPT] + list(args), capture_output=True, text=True)

    def test_default_is_help_without_reading(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn('--input', result.stdout)

    def test_pass_and_stop_exit_codes(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-held-') as folder:
            good, bad, big = (Path(folder) / n for n in ('synthetic-pass.log', 'synthetic-bad.log', 'synthetic-big.log'))
            good.write_bytes(VALID)
            bad.write_bytes(VALID.replace(b'status=0', b'status=1', 1))
            big.write_bytes(b'x' * (A.MAX_BYTES * 4))
            ok = self.run_cli('--input', str(good))
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn('PASS: held-expiry-log/1', ok.stdout)
            for path in (bad, big, Path(folder) / 'missing.log'):
                result = self.run_cli('--input', str(path))
                self.assertEqual(result.returncode, 1, path.name)
                self.assertNotIn('PASS:', result.stdout)


class OfflineOnly(unittest.TestCase):
    def test_assessor_imports_no_network_or_process_modules(self):
        tree = ast.parse((HERE / 'assess_held_expiry.py').read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split('.')[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module.split('.')[0])
        self.assertEqual(names, {'argparse', 'json', 'pathlib', 're', 'sys'})


class CodexIntegrationChecks(unittest.TestCase):
    def test_noncanonical_provider_numbers_are_malformed(self):
        for old,new in [('events=2','events=02'),('dropped=0','dropped=00'),
                        ('overflow=0','overflow=00'),('bytes=586','bytes=0586'),
                        ('lease_ms=10000','lease_ms=010000'),('index=0','index=00'),
                        ('count=100','count=0100'),('xtype=0','xtype=00')]:
            with self.subTest(field=old):
                lines=[line.replace(old,new) for line in provider_lines()]
                self.assertEqual(verdict(build(events(provider=lines))),'MALFORMED')

    def test_errno_outside_actual_sdk_type_is_malformed(self):
        for value in (2**31,2**63-1,-2**31-1):
            with self.subTest(errno=value):
                self.assertEqual(verdict(build(events(reader=reader_lines((value,value,value))))),'MALFORMED')

    def test_control_trace_gate_is_required_before_release(self):
        items=[item for item in events() if not (isinstance(item,str) and item.startswith('CONTROL_TRACE_OK'))]
        report=A.assess(build(items))
        self.assertNotEqual(report['verdict'],'PASS')
        self.assertTrue(any('premature release' in f['message'] for f in report['findings']))

    def test_trace_gate_identity_and_count_are_checked(self):
        for replacement in ('CONTROL_TRACE_OK provider=44444 events=2',
                            'CONTROL_TRACE_OK provider=%d events=3' % P):
            self.assertNotEqual(verdict(build(replace_event(events(),'CONTROL_TRACE_OK',replacement))),'PASS')

    def test_early_watchdog_cancellation_is_rejected(self):
        items=events(); items.remove('WATCHDOG_CANCELLED')
        index=next(i for i,item in enumerate(items) if isinstance(item,tuple))
        items.insert(index,'WATCHDOG_CANCELLED')
        self.assertEqual(verdict(build(items)),'CONTRADICTORY')


if __name__ == '__main__':
    unittest.main(verbosity=1)
