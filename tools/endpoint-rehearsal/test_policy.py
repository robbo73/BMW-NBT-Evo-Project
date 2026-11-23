#!/usr/bin/env python3
"""Portable bounds/readonly policy tests; no QNX server or namespace emulation."""
import ctypes
import errno
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class Policy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='nbt-endpoint-policy-')
        cls.binary = Path(cls.temp.name) / 'policy.so'
        subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                        str(ROOT / 'endpoint_policy.c'), '-o', str(cls.binary)], check=True)
        cls.lib = ctypes.CDLL(str(cls.binary))
        cls.lib.nbt_endpoint_slice.argtypes = [ctypes.c_longlong, ctypes.c_longlong,
                                               ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        cls.lib.nbt_endpoint_slice.restype = ctypes.c_int
        cls.lib.nbt_endpoint_text.restype = ctypes.c_char_p
        cls.lib.nbt_endpoint_length.restype = ctypes.c_size_t
        cls.lib.nbt_endpoint_open_allowed.argtypes = [ctypes.c_uint] * 3
        cls.lib.nbt_endpoint_open_allowed.restype = ctypes.c_int
        cls.text = cls.lib.nbt_endpoint_text()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def slice(self, offset, requested):
        start, count = ctypes.c_size_t(999), ctypes.c_size_t(999)
        error = self.lib.nbt_endpoint_slice(offset, requested, ctypes.byref(start), ctypes.byref(count))
        return error, start.value, count.value

    def test_full_read(self):
        error, start, count = self.slice(0, 4096)
        self.assertEqual((error, start), (0, 0))
        self.assertEqual(self.text[start:start + count], b'nbt-endpoint-rehearsal\n')
        self.assertEqual(count, self.lib.nbt_endpoint_length())

    def test_partial_reads_reassemble(self):
        for chunk in (1, 2, 3, 7, 23, 4096):
            position, output = 0, b''
            while True:
                error, start, count = self.slice(position, chunk)
                self.assertEqual(error, 0)
                if not count:
                    break
                output += self.text[start:start + count]
                position += count
            self.assertEqual(output, self.text)

    def test_seek_inside_text(self):
        self.assertEqual(self.slice(4, 8), (0, 4, 8))
        self.assertEqual(self.text[4:12], b'endpoint')

    def test_zero_length_read(self):
        self.assertEqual(self.slice(3, 0), (0, 3, 0))

    def test_exact_eof(self):
        n = len(self.text)
        self.assertEqual(self.slice(n, 100), (0, n, 0))

    def test_past_eof(self):
        self.assertEqual(self.slice(100, 100), (0, len(self.text), 0))

    def test_maximum_offset_does_not_wrap(self):
        self.assertEqual(self.slice(2**63 - 1, 2**63 - 1), (0, len(self.text), 0))

    def test_maximum_request_is_bounded(self):
        self.assertEqual(self.slice(1, 2**63 - 1), (0, 1, len(self.text) - 1))

    def test_negative_offset_is_rejected(self):
        self.assertEqual(self.slice(-1, 10), (errno.EINVAL, 0, 0))

    def test_negative_request_is_rejected(self):
        self.assertEqual(self.slice(0, -1), (errno.EINVAL, 0, 0))

    def test_minimum_integer_is_rejected(self):
        self.assertEqual(self.slice(-(2**63), -(2**63)), (errno.EINVAL, 0, 0))

    def test_null_outputs_are_rejected(self):
        count = ctypes.c_size_t()
        self.assertEqual(self.lib.nbt_endpoint_slice(0, 1, None, ctypes.byref(count)), errno.EINVAL)
        self.assertEqual(self.lib.nbt_endpoint_slice(0, 1, ctypes.byref(count), None), errno.EINVAL)

    def test_random_read_boundaries(self):
        randomizer = random.Random(731)
        for _ in range(4000):
            offset = randomizer.randrange(-4, 70)
            requested = randomizer.choice([0, 1, 4096, 2**31 - 1, 2**63 - 1, -1])
            error, start, count = self.slice(offset, requested)
            if offset < 0 or requested < 0:
                self.assertEqual((error, start, count), (errno.EINVAL, 0, 0))
            else:
                self.assertEqual(error, 0)
                self.assertEqual(self.text[start:start + count], self.text[offset:offset + requested])
                self.assertLessEqual(start + count, len(self.text))

    def test_read_only_open_is_allowed(self):
        self.assertEqual(self.lib.nbt_endpoint_open_allowed(1, 2, 0x300), 1)

    def test_write_create_and_truncate_are_refused(self):
        for flags in (2, 3, 0x100, 0x200, 0x301, 0xffffffff):
            self.assertEqual(self.lib.nbt_endpoint_open_allowed(flags, 2, 0x300), 0)

    def test_platform_masks_are_not_hardcoded(self):
        self.assertEqual(self.lib.nbt_endpoint_open_allowed(1, 8, 0x40), 1)
        self.assertEqual(self.lib.nbt_endpoint_open_allowed(8, 8, 0x40), 0)
        self.assertEqual(self.lib.nbt_endpoint_open_allowed(0x40, 8, 0x40), 0)


if __name__ == '__main__':
    unittest.main()
