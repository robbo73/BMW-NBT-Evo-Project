#!/usr/bin/env python3
"""Compile and exercise the C source on disposable local Linux fixtures only."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('nbt_ram_lease_rehearsal.c')


class Rehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='nbt-lease-build-')
        cls.binary = Path(cls.build.name) / 'host-rehearsal'
        subprocess.run(['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-DNBT_HOST_REHEARSAL', str(SOURCE), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nbt-lease-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def start(self, milliseconds=250):
        process = subprocess.Popen([str(self.binary), '--host-rehearse', str(self.root), str(milliseconds)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def close():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            process.stdout.close()
            process.stderr.close()
        self.addCleanup(close)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            self.assertTrue(selector.select(timeout=3), 'No READY before timeout')
            line = process.stdout.readline()
        finally:
            selector.close()
        self.assertTrue(line.startswith('READY '), line)
        base = self.root / ('.nbt-lease-rehearsal.' + str(process.pid))
        self.assertTrue((base / 'dummy-discovery/DummyTrial').is_dir())
        self.assertTrue((base / 'dummy-discovery/DummyTrial').is_symlink())
        return process, base

    def finish(self, process, code=0):
        out, err = process.communicate(timeout=4)
        self.assertEqual(process.returncode, code, out + err)
        return out, err

    def test_deadline_revokes_link_and_cleans(self):
        process, base = self.start()
        out, err = self.finish(process)
        self.assertIn('REVOKED reason=deadline', out)
        self.assertFalse(base.exists())
        self.assertFalse(err)

    def test_closed_output_client_does_not_abandon_cleanup(self):
        process, base = self.start()
        process.stdout.close()
        process.wait(timeout=4)
        self.assertEqual(process.returncode, 0)
        self.assertFalse(base.exists())

    def test_hangup_revokes_link(self):
        process, base = self.start(10000)
        process.send_signal(signal.SIGHUP)
        out, _ = self.finish(process, 2)
        self.assertIn('reason=signal', out)
        self.assertFalse(base.exists())

    def test_termination_revokes_link(self):
        process, base = self.start(10000)
        process.terminate()
        self.finish(process, 2)
        self.assertFalse(base.exists())

    def test_interrupt_revokes_link(self):
        process, base = self.start(10000)
        process.send_signal(signal.SIGINT)
        self.finish(process, 2)
        self.assertFalse(base.exists())

    def test_unrelated_process_restart_does_not_cancel_expiry(self):
        process, base = self.start(700)
        # This is an unrelated local process, not a simulated HMI implementation.
        other = subprocess.Popen(['sleep', '10'])
        other.terminate()
        other.wait(timeout=3)
        self.finish(process)
        self.assertFalse(base.exists())

    def test_missing_dummy_target_still_cleans_link(self):
        process, base = self.start()
        (base / 'dummy-target').rmdir()
        self.finish(process)
        self.assertFalse(base.exists())

    def test_changed_link_is_preserved_and_reported(self):
        process, base = self.start()
        link = base / 'dummy-discovery/DummyTrial'
        link.unlink()
        link.symlink_to(self.root / 'foreign-target')
        _, err = self.finish(process, 1)
        self.assertIn('preserving fixture', err)
        self.assertEqual(os.readlink(link), str(self.root / 'foreign-target'))

    def test_nonempty_target_is_preserved_after_revoking_link(self):
        process, base = self.start()
        foreign = base / 'dummy-target/keep'
        foreign.write_text('preserve')
        self.finish(process, 1)
        self.assertEqual(foreign.read_text(), 'preserve')
        self.assertFalse((base / 'dummy-discovery/DummyTrial').is_symlink())

    def test_sigkill_is_explicitly_not_recovery(self):
        process, base = self.start(10000)
        process.kill()
        self.finish(process, -signal.SIGKILL)
        self.assertTrue((base / 'dummy-discovery/DummyTrial').is_symlink())

    def test_linked_root_is_refused_without_writes(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        result = subprocess.run([str(self.binary), '--host-rehearse', str(alias), '250'], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(self.root.iterdir()), [alias])

    def test_bad_arguments_do_not_write(self):
        for arguments in (['activate'], ['--host-rehearse', str(self.root), '0'],
                          ['--host-rehearse', str(self.root), 'abc']):
            result = subprocess.run([str(self.binary)] + arguments, capture_output=True)
            self.assertEqual(result.returncode, 2)
        self.assertFalse(list(self.root.iterdir()))

    def test_default_is_help_only(self):
        result = subprocess.run([str(self.binary)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('No plugin activation', result.stdout)
        self.assertFalse(list(self.root.iterdir()))


if __name__ == '__main__':
    unittest.main()
