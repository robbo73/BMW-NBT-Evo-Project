#!/usr/bin/env python3
"""Host file/stdio checks, not QNX IPC, XML parsing or HMI emulation."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
from test_body import expected_body
BODY = expected_body(586)


class StdioReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='nbt-stdio-host-')
        cls.root = Path(cls.temp.name)
        source = (ROOT / 'nbt_large_reader.c').read_text()
        assert source.count('/ramdisk/mm') == 1
        private_source = cls.root / 'reader.c'
        private_source.write_text(source.replace('/ramdisk/mm', str(cls.root)))
        cls.binary = cls.root / 'reader'
        cls.fault_binary = cls.root / 'fault-reader'
        command = ['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-I',str(ROOT),str(private_source),str(ROOT/'large_body.c')]
        subprocess.run(command + ['-o', str(cls.binary)], check=True)
        wrappers = ['-Wl,--wrap=' + name for name in ('fopen', 'fseek', 'ftell', 'fread', 'fclose')]
        subprocess.run(command + [str(ROOT / 'test_support/stdio_faults.c'), *wrappers,
                                 '-o', str(cls.fault_binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.fixture = self.root / '.nbt-large-alias-586.42'
        self.fixture.mkdir()
        self.target = self.root / 'dummy-target'
        self.target.write_bytes(BODY)
        self.alias = self.fixture / 'dummy-body.bin'
        self.alias.symlink_to(self.target)

    def tearDown(self):
        if self.fixture.is_symlink():
            self.fixture.unlink()
            self.moved.rename(self.fixture)
        for item in self.fixture.iterdir():
            item.unlink()
        self.fixture.rmdir()
        self.target.unlink(missing_ok=True)

    def run_reader(self, args=('--read-alias', '42'), fault=None):
        return subprocess.run([str(self.fault_binary if fault else self.binary), *args],
                              env=dict(os.environ, NBT_STDIO_FAULT=fault or ''),
                              capture_output=True, text=True, timeout=8)

    def assert_failure(self, result):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn('PASS:', result.stdout)
        self.assertEqual(self.target.read_bytes(), BODY)
        self.assertTrue(self.alias.is_symlink())

    def test_exact_dummy_alias_passes_and_stays_unchanged(self):
        result = self.run_reader()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('bytes=586 items=1', result.stdout)
        self.assertIn('seek-end/tell/rewind/read/close', result.stdout)
        self.assertEqual(self.target.read_bytes(), BODY)
        self.assertTrue(self.alias.is_symlink())

    def test_default_help_does_not_require_alias(self):
        self.alias.unlink()
        for args in ((), ('--help',)):
            result = self.run_reader(args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('help performs no file reads', result.stdout)
            self.assertNotIn('PASS:', result.stdout)

    def test_bad_modes_and_pid_forms_are_refused(self):
        bad = ['', '0', '1', '01', '042', '-42', '+42', ' 42', '42 ', '42x',
               '../42', '2147483648', '999999999999999999999999999999']
        for args in [('activate',), ('--read-alias',), ('--read-alias', '42', 'extra')]+[
                ('--read-alias', pid) for pid in bad]:
            with self.subTest(args=args):
                result = self.run_reader(args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn('PASS:', result.stdout)

    def test_pid_upper_limit_is_parsed_without_overflow(self):
        result = self.run_reader(('--read-alias', '2147483647'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('parent', result.stderr)

    def test_regular_alias_replacement_is_refused(self):
        self.alias.unlink()
        self.alias.write_bytes(BODY)
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('not a symlink', result.stderr)
        self.assertEqual(self.alias.read_bytes(), BODY)

    def test_linked_parent_is_refused(self):
        self.moved = self.root / 'moved-fixture'
        self.fixture.rename(self.moved)
        self.fixture.symlink_to(self.moved, target_is_directory=True)
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('parent', result.stderr)
        self.assertTrue(self.fixture.is_symlink())

    def test_dangling_alias_is_refused(self):
        self.target.unlink()
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('wrong type or size', result.stderr)
        self.assertTrue(self.alias.is_symlink())

    def test_directory_target_is_refused(self):
        self.alias.unlink()
        self.alias.symlink_to(self.fixture, target_is_directory=True)
        result = self.run_reader()
        self.assert_failure(result)

    def test_wrong_sizes_are_refused_before_full_read(self):
        for body in (b'', BODY[:-1], BODY+b'x', BODY*100):
            with self.subTest(size=len(body)):
                self.target.write_bytes(body)
                result = self.run_reader()
                self.assertEqual(result.returncode, 1)
                self.assertIn('wrong type or size', result.stderr)
                self.assertNotIn('PASS:', result.stdout)
                self.assertEqual(self.target.read_bytes(), body)

    def test_wrong_same_size_bytes_are_refused_without_echo(self):
        body = b'x' * len(BODY)
        self.target.write_bytes(body)
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('unexpected dummy bytes', result.stderr)
        self.assertNotIn(body.decode(), result.stdout + result.stderr)
        self.assertEqual(self.target.read_bytes(), body)

    def test_stdio_errors_cannot_report_success(self):
        for fault in ('open', 'seek_end', 'tell', 'seek_start', 'read', 'close'):
            with self.subTest(fault=fault):
                result = self.run_reader(fault=fault)
                self.assert_failure(result)

    def test_full_reader_at_8193_bytes(self):
        binary=self.root/'reader-8193'
        subprocess.run(['cc','-std=gnu99','-O2','-Wall','-Wextra','-Werror',
                        '-DNBT_BODY_LENGTH=8193','-I',str(ROOT),str(self.root/'reader.c'),
                        str(ROOT/'large_body.c'),'-o',str(binary)],check=True)
        parent=self.root/'.nbt-large-alias-8193.42'
        target=self.root/'large-target'
        parent.mkdir();target.write_bytes(expected_body(8193))
        alias=parent/'dummy-body.bin';alias.symlink_to(target)
        try:
            result=subprocess.run([str(binary),'--read-alias','42'],capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('bytes=8193 items=1',result.stdout)
            self.assertEqual(target.read_bytes(),expected_body(8193))
        finally:
            alias.unlink();parent.rmdir();target.unlink();binary.unlink()

    def test_alarm_bounds_a_blocked_reader(self):
        result = self.run_reader(fault='hang_read')
        self.assertEqual(result.returncode, -signal.SIGALRM, result.stdout + result.stderr)
        self.assertNotIn('PASS:', result.stdout)
        self.assertEqual(self.target.read_bytes(), BODY)


if __name__ == '__main__':
    unittest.main(verbosity=2)
