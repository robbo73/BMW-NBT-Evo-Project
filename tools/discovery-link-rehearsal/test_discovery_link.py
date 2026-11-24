#!/usr/bin/env python3
"""Shell control-flow fixtures only; ordinary Linux files, no QNX IPC model."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import unittest

SOURCE = Path(__file__).with_name('check_discovery_link.sh').read_text()


class DiscoveryLink(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nbt-alias-shell-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ram = self.root / 'ram'
        self.ram.mkdir()
        self.helper = self.root / 'helper'
        self.helper.write_text('''#!/usr/bin/env python3
import os, signal, time
from pathlib import Path
root = Path(__file__).parent
endpoint = root / ('endpoint.' + str(os.getpid()))
scenario = os.environ.get('NBT_FIXTURE', 'normal')
def stop(number, frame):
    endpoint.unlink(missing_ok=True)
    raise SystemExit(2)
signal.signal(signal.SIGTERM, stop)
if scenario == 'no_endpoint':
    raise SystemExit(1)
endpoint.write_text('wrong\\n' if scenario == 'wrong' else 'nbt-endpoint-rehearsal\\n')
if scenario == 'unexpected':
    next((root / 'ram').glob('.nbt-endpoint-alias.*')).joinpath('.unexpected').write_text('preserve')
if scenario == 'overrun':
    time.sleep(30)
else:
    time.sleep(0.3)
endpoint.unlink(missing_ok=True)
raise SystemExit(0)
''')
        self.helper.chmod(0o700)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        sleep = self.bin / 'sleep'
        sleep.write_text('#!/usr/bin/env python3\nimport sys,time\ntime.sleep(float(sys.argv[1])*0.05)\n')
        sleep.chmod(0o700)
        self.script = self.root / 'check.sh'
        self.script.write_text(SOURCE.replace('/ramdisk/mm', str(self.ram))
                              .replace('/dev/shmem/nbt_endpoint_rehearsal_83c6e473829e', str(self.helper))
                              .replace('/dev/nbt_endpoint_rehearsal.', str(self.root / 'endpoint.')))
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def run_check(self, args=(), scenario='normal'):
        result = subprocess.run(['sh', str(self.script), *args],
                                env=dict(self.env, NBT_FIXTURE=scenario),
                                capture_output=True, text=True, timeout=5)
        return result

    def assert_clean(self):
        self.assertEqual(list(self.ram.iterdir()), [])

    def test_help_and_bad_arguments_do_not_create_fixtures(self):
        for args, code in (((), 0), (('--help',), 0), (('--bad',), 2),
                           (('--deadline', 'extra'), 2)):
            result = self.run_check(args)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            self.assert_clean()
            self.assertEqual(list(self.root.glob('endpoint.*')), [])

    def test_missing_executable_is_refused(self):
        self.helper.unlink()
        result = self.run_check(('--deadline',))
        self.assertEqual(result.returncode, 1)
        self.assertIn('executable unavailable', result.stdout)
        self.assert_clean()

    def test_linked_executable_is_refused(self):
        target = self.root / 'real-helper'
        self.helper.rename(target)
        self.helper.symlink_to(target)
        result = self.run_check(('--deadline',))
        self.assertEqual(result.returncode, 1)
        self.assert_clean()

    def test_linked_root_is_refused(self):
        target = self.root / 'real-ram'
        self.ram.rename(target)
        self.ram.symlink_to(target, target_is_directory=True)
        result = self.run_check(('--deadline',))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(target.iterdir()), [])

    def test_deadline_reads_alias_checks_dangling_and_cleans(self):
        result = self.run_check(('--deadline',))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ALIAS_READ: nbt-endpoint-rehearsal', result.stdout)
        self.assertIn('DANGLING:', result.stdout)
        self.assertIn('PASS: --deadline', result.stdout)
        self.assert_clean()

    def test_forced_death_rejects_surviving_ordinary_file(self):
        result = self.run_check(('--forced-death',))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Endpoint server exit: 137', result.stdout)
        self.assertIn('still resolves', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
        self.assert_clean()
        self.assertEqual(len(list(self.root.glob('endpoint.*'))), 1)

    def test_forced_death_success_branch_with_explicit_external_unlink_fixture(self):
        # A test-only thread unlinks an ordinary file after its writer dies.
        # This tests shell branch order, NOT QNX automatic endpoint revocation.
        stopped = threading.Event()
        def external_unlink():
            while not stopped.wait(0.002):
                for endpoint in self.root.glob('endpoint.*'):
                    pid = int(endpoint.name.split('.')[-1])
                    try:
                        stat = Path('/proc', str(pid), 'stat').read_text()
                        dead = stat.rsplit(')', 1)[1].split()[0] == 'Z'
                    except FileNotFoundError:
                        dead = True
                    if dead:
                        endpoint.unlink(missing_ok=True)
        thread = threading.Thread(target=external_unlink)
        thread.start()
        try:
            result = self.run_check(('--forced-death',))
        finally:
            stopped.set()
            thread.join()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Endpoint server exit: 137', result.stdout)
        self.assertIn('PASS: --forced-death', result.stdout)
        self.assert_clean()

    def test_wrong_text_fails_and_cleans(self):
        result = self.run_check(('--deadline',), 'wrong')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('unexpected text', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
        self.assert_clean()

    def test_missing_endpoint_fails_and_cleans(self):
        result = self.run_check(('--deadline',), 'no_endpoint')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('endpoint not ready', result.stdout)
        self.assert_clean()

    def test_unexpected_hidden_file_is_preserved(self):
        result = self.run_check(('--deadline',), 'unexpected')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('unexpected fixture entry', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
        fixture, = self.ram.iterdir()
        self.assertEqual((fixture / '.unexpected').read_text(), 'preserve')
        self.assertFalse((fixture / 'dummy-discovery.txt').is_symlink())

    def test_hangup_cleans_owned_alias_and_directory(self):
        process = subprocess.Popen(['sh', str(self.script), '--deadline'],
                                   env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if any(p.is_symlink() for p in self.ram.glob('*/dummy-discovery.txt')):
                    break
                time.sleep(0.005)
            else:
                self.fail('fixture alias never appeared')
            process.send_signal(signal.SIGHUP)
            out, err = process.communicate(timeout=4)
            self.assertEqual(process.returncode, 2, out + err)
            self.assertNotIn('PASS:', out)
            self.assert_clean()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_closed_output_does_not_abandon_cleanup(self):
        process = subprocess.Popen(['sh', str(self.script), '--deadline'],
                                   env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process.stdout.close()
        try:
            status = process.wait(timeout=4)
            errors = process.stderr.read()
            self.assertEqual(status, 0, errors)
            self.assert_clean()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stderr.close()

    def test_overrun_watchdog_cannot_count_as_deadline_pass(self):
        result = self.run_check(('--deadline',), 'overrun')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('WATCHDOG:', result.stdout)
        self.assertIn('unexpected helper exit', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
        self.assert_clean()


if __name__ == '__main__':
    unittest.main(verbosity=2)
