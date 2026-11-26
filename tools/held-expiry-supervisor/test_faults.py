#!/usr/bin/env python3
"""Namespace-free fault regressions for the revision-2 supervisor. SYNTHETIC only.

These need no root, namespace, chroot or production path. test_support/fault_unit.c
includes the unchanged supervisor source with clock_gettime, waitpid, write, kill,
pread and fork routed through injectable wrappers, and shortened unit timings
(trial 0.4 s, output 0.7 s, launcher hard stop 1 s, self-kill 1.5 s). In-process
scenarios call the real functions; launcher scenarios fork real stand-in supervisor
bodies. Injected faults are not QNX observations.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
import uuid

HERE = Path(__file__).resolve().parent


def build_unit(directory):
    binary = Path(directory) / 'fault_unit'
    subprocess.run(['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-DNBT_SUPERVISOR_SOURCE="%s"' % (HERE / 'nbt_held_supervisor.c'),
                    str(HERE / 'test_support' / 'fault_unit.c'), '-o', str(binary), '-lrt'], check=True)
    return binary


def process_gone(pid):
    try:
        state = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0]
    except OSError:
        return True
    return state in ('Z', 'X')


def wait_for_file(path, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            text = Path(path).read_text().strip()
            if text:
                return int(text)
        except (OSError, ValueError):
            pass
        time.sleep(0.01)
    raise AssertionError('timed out waiting for ' + str(path))


class FaultUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='nbt-fault-unit-')
        cls.dir = Path(cls.temp.name)
        cls.unit = build_unit(cls.dir)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def scenario(self, name):
        result = subprocess.run([str(self.unit), 'in-process', name], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def launcher(self, child, fault=None, **extra_env):
        """Start one launcher; its stand-in writes its PID to a fresh, unique ready file."""
        self.ready = self.dir / ('ready-%s' % uuid.uuid4().hex)
        env = dict(os.environ, NBT_UNIT_CHILD=child, NBT_UNIT_READY=str(self.ready))
        env.pop('NBT_UNIT_FAULT', None)
        if fault:
            env['NBT_UNIT_FAULT'] = fault
        env.update(extra_env)
        return subprocess.Popen([str(self.unit), 'launcher'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


class ClockFailure(FaultUnit):
    def test_mid_trial_failure_stops_the_trial_explicitly(self):
        r = self.scenario('clock_fails_mid_trial')
        self.assertEqual((r['trial_expired'], r['stopped'], r['clock_failed'], r['abort_clock']), (1, 1, 1, 1))
        self.assertEqual(r['watchdog_provider'], 0)          # reported as clock failure, not a deadline
        self.assertEqual(r['output_expired'], 0)              # output then bounded by ticks and hard stops

    def test_backwards_clock_is_a_failure_not_a_negative_elapsed(self):
        r = self.scenario('clock_goes_backwards')
        self.assertEqual((r['trial_expired'], r['stopped'], r['clock_failed'], r['abort_clock']), (1, 1, 1, 1))

    def test_kernel_ticks_decide_even_if_the_clock_reads_do_not_advance(self):
        r = self.scenario('ticks_override_stuck_clock')
        self.assertEqual(r['before_tick'], 0)
        self.assertEqual((r['output_at_limit'], r['output_past_limit']), (0, 1))
        self.assertEqual((r['stopped'], r['watchdog_reader'], r['clock_failed']), (1, 1, 0))

    def test_forced_collection_is_bounded_without_a_clock(self):
        r = self.scenario('clock_fails_during_forced_collection')
        self.assertEqual((r['settled'], r['still_owned'], r['kill_kill'], r['abort_unreaped']), (0, 1, 1, 1))

    def test_cleanup_deadline_and_clock_failure_prevent_watchdog_cancelled(self):
        self.assertEqual(self.scenario('cleanup_on_time')['watchdog_cancelled'], 1)
        r = self.scenario('deadline_during_cleanup')
        self.assertEqual((r['watchdog_cancelled'], r['abort_cleanup_deadline'], r['trial_failed']), (0, 1, 1))
        r = self.scenario('clock_fails_during_cleanup')
        self.assertEqual((r['watchdog_cancelled'], r['abort_clock'], r['trial_failed']), (0, 1, 1))

    def test_clock_failure_after_a_complete_log_is_a_nonzero_exit(self):
        self.assertEqual(self.scenario('clock_failed_but_written')['exit_code'], 3)

    def test_startup_clock_failure_refuses_before_any_child(self):
        for role in ('launcher', 'supervisor'):
            env = dict(os.environ, NBT_UNIT_FAULT='clock_fail', NBT_UNIT_CHILD='exit:0')
            result = subprocess.run([str(self.unit), role], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2, role)
            self.assertIn('monotonic clock unavailable at startup', result.stderr)
            self.assertNotIn('UNIT_FORK', result.stderr)


class LateWrite(FaultUnit):
    def test_write_completing_after_the_output_deadline_fails(self):
        for name in ('write_completes_late', 'partial_write_late'):
            r = self.scenario(name)
            self.assertEqual((r['write_log'], r['exit_code']), (-1, 3), name)

    def test_write_completing_on_time_succeeds(self):
        r = self.scenario('write_on_time')
        self.assertEqual((r['write_log'], r['exit_code']), (0, 0))


class WaitErrors(FaultUnit):
    def test_echild_relinquishes_and_the_pid_is_never_signalled(self):
        r = self.scenario('waitpid_echild')
        self.assertEqual((r['result'], r['owned'], r['lost'], r['collected']), (2, 0, 1, 0))
        self.assertEqual((r['signal_owned'], r['kill_calls']), (-1, 0))
        self.assertEqual((r['settled'], r['abort_lost']), (0, 1))  # fixture kept: status never collected

    def test_other_wait_errors_keep_ownership_and_fail_bounded(self):
        r = self.scenario('waitpid_eio')
        self.assertEqual((r['result'], r['owned'], r['child_event']), (3, 1, -1))
        self.assertGreater(r['wait_errors'], 0)
        self.assertEqual(r['signal_owned'], 0)                 # still signalable: PID still reserved
        self.assertEqual((r['settled'], r['abort_wait_error']), (0, 1))

    def test_interrupted_waits_retry_then_collect(self):
        r = self.scenario('waitpid_eintr_then_collect')
        self.assertEqual((r['result'], r['owned'], r['collected'], r['status']), (1, 0, 1, 0))

    def test_endless_interruption_is_bounded_and_keeps_ownership(self):
        r = self.scenario('waitpid_eintr_forever')
        self.assertEqual((r['result'], r['owned'], r['wait_errors']), (3, 1, 1))


class ReleaseGate(FaultUnit):
    def test_deadline_passing_during_the_final_read_prevents_release(self):
        r = self.scenario('release_deadline_during_final_read')
        self.assertEqual((r['gate'], r['kill_usr1'], r['release_sent'], r['watchdog_reader']), (-1, 0, 0, 1))

    def test_release_on_time_sends_exactly_one_usr1(self):
        r = self.scenario('release_on_time')
        self.assertEqual((r['gate'], r['kill_usr1'], r['release_sent']), (0, 1, 1))


class Launcher(FaultUnit):
    def run_launcher(self, child, fault=None):
        proc = self.launcher(child, fault)
        out, err = proc.communicate(timeout=20)
        return proc.returncode, err

    def test_supervisor_exit_status_is_propagated(self):
        for child, expected in (('exit:0', 0), ('exit:1', 1), ('exit:2', 2), ('exit:3', 3), ('signal:11', 139)):
            rc, err = self.run_launcher(child)
            self.assertEqual(rc, expected, child)
            self.assertNotIn('UNIT_KILL', err, child)

    def test_hard_stop_kills_only_the_owned_supervisor(self):
        started = time.monotonic()
        rc, err = self.run_launcher('hang')
        elapsed = time.monotonic() - started
        self.assertEqual(rc, 123)
        self.assertGreaterEqual(elapsed, 0.9)
        self.assertLess(elapsed, 2.0)
        pid = int(self.ready.read_text())
        self.assertEqual(err.count('UNIT_KILL'), 1)
        self.assertIn('UNIT_KILL pid=%d sig=9' % pid, err)
        self.assertTrue(process_gone(pid))

    def test_launcher_echild_never_signals(self):
        rc, err = self.run_launcher('exit:0', fault='wait_echild')
        self.assertEqual(rc, 124)
        self.assertNotIn('UNIT_KILL', err)

    def test_launcher_wait_errors_keep_ownership_and_are_bounded(self):
        started = time.monotonic()
        rc, err = self.run_launcher('hang', fault='wait_eio')
        self.assertEqual(rc, 125)                              # never collectable here
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(err.count('UNIT_KILL'), 1)            # the owned supervisor was still stopped
        rc, err = self.run_launcher('exit:0', fault='wait_eio_twice')
        self.assertEqual(rc, 122)                              # collected, but anomaly is not acceptance

    def test_external_signals_are_forwarded_to_the_supervisor_only(self):
        for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            with self.subTest(signal=number):
                record, grand_record, grand_pid = (self.dir / ('rec-%d' % number), self.dir / ('grec-%d' % number),
                                                   self.dir / ('gpid-%d' % number))
                for path in (record, grand_record, grand_pid):
                    path.unlink(missing_ok=True)
                proc = self.launcher('record_signals', NBT_UNIT_RECORD=str(record),
                                     NBT_UNIT_GRANDCHILD_RECORD=str(grand_record), NBT_UNIT_GRANDCHILD_PID=str(grand_pid))
                wait_for_file(self.ready)
                grandchild = wait_for_file(grand_pid)
                proc.send_signal(number)
                if number != signal.SIGTERM:
                    time.sleep(0.2)
                    proc.send_signal(signal.SIGTERM)       # the stand-in exits on TERM only
                _, err = proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 1)
                received = record.read_text().split()
                self.assertEqual(received[0], '%02d' % number)
                self.assertFalse(grand_record.exists() and grand_record.read_text().strip(),
                                 'grandchild must not be signalled')
                self.assertFalse(process_gone(grandchild))   # untouched by the launcher
                self.assertNotIn('pid=%d ' % grandchild, err)
                os.kill(grandchild, signal.SIGKILL)

    def test_supervisor_killed_externally_is_reported_and_nothing_else_signalled(self):
        proc = self.launcher('hang')
        pid = wait_for_file(self.ready)
        os.kill(pid, signal.SIGKILL)             # pid is the launcher's still-unreaped child
        _, err = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 137)
        self.assertNotIn('UNIT_KILL', err)

    def test_launcher_death_leaves_the_supervisor_self_bounded(self):
        proc = self.launcher('selfkill')
        pid = wait_for_file(self.ready)
        proc.kill()                                            # launcher gone: no hard stop from it
        proc.communicate(timeout=10)
        started = time.monotonic()
        while not process_gone(pid) and time.monotonic() - started < 5:
            time.sleep(0.02)
        self.assertTrue(process_gone(pid), 'self-addressed SIGKILL timer must end the supervisor')
        self.assertLess(time.monotonic() - started, 2.5)


class Gate(unittest.TestCase):
    """The acceptance gate needs only the unchanged assessor, no namespaces."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location('gate_trial', HERE / 'gate_trial.py')
        cls.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gate)
        cls.assessor = cls.gate.load_assessor()
        example = HERE.parent / 'held-expiry-assessor' / 'examples' / 'SYNTHETIC-held-expiry-pass.log'
        cls.passing = example.read_bytes()

    def test_synthetic_example_passes_the_assessor(self):
        self.assertEqual(self.assessor.assess(self.passing)['verdict'], 'PASS')

    def test_accept_needs_exit_zero_and_pass(self):
        self.assertEqual(self.gate.decide(0, self.passing, self.assessor)['decision'], 'ACCEPT')
        for code in (1, 2, 3, 122, 123, 124, 125, 137, -9):
            self.assertEqual(self.gate.decide(code, self.passing, self.assessor)['decision'], 'REJECT', code)
        self.assertEqual(self.gate.decide(0, self.passing[:-5], self.assessor)['decision'], 'REJECT')

    def test_cli_requires_the_exit_status(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'synthetic.log'
            log.write_bytes(self.passing)
            script = str(HERE / 'gate_trial.py')
            self.assertEqual(subprocess.run(['python3', '-B', script, '--input', str(log)], capture_output=True).returncode, 2)
            ok = subprocess.run(['python3', '-B', script, '--controller-exit', '0', '--input', str(log)], capture_output=True, text=True)
            self.assertEqual((ok.returncode, ok.stdout.strip().splitlines()[-1]), (0, 'ACCEPT'))
            late = subprocess.run(['python3', '-B', script, '--controller-exit', '3', '--input', str(log)], capture_output=True, text=True)
            self.assertEqual((late.returncode, late.stdout.strip().splitlines()[-1]), (1, 'REJECT'))


class CodexReviewRegressions(FaultUnit):
    def test_clock_failure_stays_expired_after_recovery(self):
        r = self.scenario('clock_recovers_after_failure')
        self.assertEqual((r['first_expired'], r['recovered_expired'], r['stopped']), (1,1,1))
    def test_clock_cannot_regress_relative_to_last_good_read(self):
        r = self.scenario('clock_backwards_after_good_read')
        self.assertEqual((r['first_result'], r['second_result'], r['clock_failed']), (0,-1,1))
    def test_signal_handlers_preserve_errno(self):
        r = self.scenario('handler_preserves_errno')
        self.assertEqual(r['supervisor_errno'], r['expected_eio'])
        self.assertEqual(r['launcher_errno'], r['expected_echild'])
    def test_large_timer_overrun_saturates_without_wrapping(self):
        r = self.scenario('handler_saturates_overrun')
        self.assertEqual((r['ticks'],r['launcher_ticks']), (1000000,1000000))


if __name__ == '__main__':
    unittest.main(verbosity=1)
