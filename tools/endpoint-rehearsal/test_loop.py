#!/usr/bin/env python3
"""Real main-loop control flow with host-only receive stubs, never a QNX emulator."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class DispatchLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='nbt-endpoint-loop-')
        cls.binary = Path(cls.temp.name) / 'host-loop'
        subprocess.run(['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-DNBT_ENDPOINT_TEST_RUNTIME', str(ROOT / 'nbt_endpoint_rehearsal.c'),
                        str(ROOT / 'endpoint_policy.c'), str(ROOT / 'test_support/fake_qnx.c'),
                        '-Wl,--wrap=lstat', '-Wl,--wrap=clock_gettime', '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, scenario, expected):
        env = dict(os.environ, NBT_TEST_SCENARIO=scenario)
        result = subprocess.run([str(self.binary), '--serve'], env=env,
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertIn('invalid=0 detaches=1 frees=1', result.stdout)
        if expected == 0:
            self.assertIn('handlers=2', result.stdout)
            self.assertIn('DETACHED reason=deadline', result.stdout)
            self.assertFalse(result.stderr)
        else:
            self.assertNotIn('DETACHED reason=deadline', result.stdout)
        return result

    def test_nonnull_timeout_context_is_not_dispatched(self):
        self.run_case('timeout_context', 0)

    def test_null_timeout_keeps_original_context(self):
        self.run_case('null_timeout', 0)

    def test_interrupt_retries(self):
        self.run_case('interrupted', 0)

    def test_nonnull_receive_failure_remains_fatal(self):
        self.run_case('receive_error', 1)

    def test_null_receive_failure_remains_fatal(self):
        self.run_case('null_error', 1)

    def test_negative_receive_id_without_errno_is_fatal(self):
        self.run_case('missing_error', 1)

    def test_actual_handler_failure_remains_fatal(self):
        self.run_case('handler_error', 1)

    def test_handler_timeout_is_not_blindly_swallowed(self):
        self.run_case('handler_timeout', 1)

    def test_help_and_bad_args_never_set_up_dispatch(self):
        for args, expected in (([], 0), (['--help'], 0), (['activate'], 2)):
            result = subprocess.run([str(self.binary)] + args, capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, expected)
            self.assertNotIn('READY', result.stdout)
            self.assertNotIn('MOCK_LOOP', result.stdout)


if __name__ == '__main__':
    unittest.main()
