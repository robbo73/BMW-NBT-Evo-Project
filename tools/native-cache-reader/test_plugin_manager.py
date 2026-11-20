import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from nbt_native_cache import CacheGraph, Refuse, main
from plugin_manager import inspect_manager
from test_native_cache import BASES, LAYOUT, Memory


PROFILE = json.loads(Path(__file__).with_name('manager-layout.json').read_text())
MANAGER = 0x3000000
NODES = [0x3000100, 0x3000200, 0x3000300]
STRINGS = [0x3001000, 0x3001100, 0x3001200]


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.memory = Memory()
        self.profile = copy.deepcopy(PROFILE)
        self.profile['fingerprints'] = [{'offset': 0x100000, 'bytes': 4,
                                         'sha256': hashlib.sha256(b'TEST').hexdigest()}]
        self.memory.add(0x100000, 4)
        self.memory.put(0x100000, b'TEST')
        self.memory.add(PROFILE['instance_pointer'], 4)
        self.memory.words(PROFILE['instance_pointer'], MANAGER)
        self.memory.add(MANAGER, 0x68)
        self.memory.words(MANAGER, PROFILE['manager_vtable'])
        self.memory.words(MANAGER + 0x1c, 0, NODES[1], NODES[0], NODES[2], 3)
        self.memory.put(MANAGER + 0x54, b'\1')
        self.memory.put(MANAGER + 0x5c, b'\1')
        for index, name in enumerate((b'/a/Plugins', b'/b/PluginsCoded', b'/c/Plugins')):
            self.memory.add(NODES[index], 24)
            parent = MANAGER + 0x1c if index == 1 else NODES[1]
            left, right = (NODES[0], NODES[2]) if index == 1 else (0, 0)
            self.memory.words(NODES[index], 1, parent, left, right, STRINGS[index])
            self.memory.put(NODES[index] + 0x14, bytes([index == 1]))
            self.memory.add(STRINGS[index] - 12, 128)
            # BMW BasicString refcount/capacity/length, not GNU's length/capacity/refcount.
            self.memory.words(STRINGS[index] - 12, 1, len(name), len(name))
            self.memory.put(STRINGS[index], name + b'\0')
        self.graph = CacheGraph(self.memory, BASES, LAYOUT)

    def result(self):
        return inspect_manager(self.graph, self.profile)

    def test_existing_paths_and_coded_flags(self):
        report = self.result()
        self.assertEqual([r['path'] for r in report['directories']],
                         ['/a/Plugins', '/b/PluginsCoded', '/c/Plugins'])
        self.assertEqual([r['coded_name_filter'] for r in report['directories']], [False, True, False])
        self.assertFalse(report['plugin_loading_verified'])
        self.assertEqual(report['snapshot_consistency'], 'best_effort_rechecked_not_atomic')

    def test_empty_registered_tree(self):
        end = MANAGER + 0x1c
        self.memory.words(end, 0, 0, end, end, 0)
        self.assertEqual(self.result()['directories'], [])

    def test_malformed_empty_tree_refused(self):
        self.memory.words(MANAGER + 0x2c, 0)
        with self.assertRaisesRegex(Refuse, 'empty'):
            self.result()

    def test_wrong_code_stops_before_pointer_read(self):
        self.memory.put(0x100000, b'FAIL')
        with self.assertRaisesRegex(Refuse, 'fingerprint'):
            self.result()
        self.assertEqual(self.memory.reads, [(0x100000, 4)])

    def test_absent_singleton_is_not_initialized(self):
        self.memory.words(PROFILE['instance_pointer'], 0)
        with self.assertRaisesRegex(Refuse, 'pointer'):
            self.result()

    def test_wrong_type_refused(self):
        self.memory.words(MANAGER, 0x12340000)
        with self.assertRaisesRegex(Refuse, 'vtable'):
            self.result()

    def test_excessive_count_refused(self):
        self.memory.words(MANAGER + 0x2c, 17)
        with self.assertRaisesRegex(Refuse, 'count'):
            self.result()

    def test_cycle_refused(self):
        self.memory.words(NODES[0] + 8, NODES[1])
        with self.assertRaisesRegex(Refuse, 'cycle'):
            self.result()

    def test_wrong_parent_refused(self):
        self.memory.words(NODES[0] + 4, MANAGER)
        with self.assertRaisesRegex(Refuse, 'parent'):
            self.result()

    def test_wrong_extrema_refused(self):
        self.memory.words(MANAGER + 0x24, NODES[1])
        with self.assertRaisesRegex(Refuse, 'extrema'):
            self.result()

    def test_unordered_paths_refused(self):
        self.memory.put(STRINGS[0], b'/z/Plugins\0')
        with self.assertRaisesRegex(Refuse, 'unordered'):
            self.result()

    def test_bad_coded_flag_refused(self):
        self.memory.put(NODES[1] + 0x14, b'\2')
        with self.assertRaisesRegex(Refuse, 'coded'):
            self.result()

    def test_gnu_header_layout_is_not_accepted_as_bmw(self):
        self.memory.words(STRINGS[0] - 12, 10, 10, 10000)
        with self.assertRaisesRegex(Refuse, 'length'):
            self.result()

    def test_unterminated_path_refused(self):
        self.memory.put(STRINGS[0] + len(b'/a/Plugins'), b'!')
        with self.assertRaisesRegex(Refuse, 'string'):
            self.result()

    def test_changed_path_refused_on_recheck(self):
        original = self.memory.read
        def changing(address, size):
            data = original(address, size)
            if address == STRINGS[0]:
                self.memory.put(address, b'/z/Plugins\0')
            return data
        self.memory.read = changing
        with self.assertRaisesRegex(Refuse, 'changed'):
            self.result()

    def test_observation_does_not_write_fixture(self):
        before = {a: bytes(b) for a, b in self.memory.parts.items()}
        self.result()
        self.assertEqual(before, {a: bytes(b) for a, b in self.memory.parts.items()})

    def test_manager_requires_explicit_cache_mode(self):
        with patch.object(sys, 'argv', ['nbt_native_cache.py', '--pid', '278582', '--inspect-manager']), \
             patch('nbt_native_cache.SSHMemory') as remote, \
             patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as result:
                main()
            self.assertEqual(result.exception.code, 2)
            remote.assert_not_called()

    def test_real_script_and_optional_inspector_share_refusal_type(self):
        # A real script run previously imported a second nbt_native_cache copy.
        script = Path(__file__).with_name('nbt_native_cache.py')
        code = '''
import contextlib, io, runpy, sys
from pathlib import Path
path = Path(sys.argv[1])
sys.path.insert(0, str(path.parent))
sys.argv = [str(path), '--help']
with contextlib.redirect_stdout(io.StringIO()):
    try:
        runpy.run_path(str(path), run_name='__main__')
    except SystemExit as result:
        assert result.code == 0
import nbt_native_cache, plugin_manager
assert nbt_native_cache.__name__ == '__main__'
assert plugin_manager.require is nbt_native_cache.require
try:
    plugin_manager.require(False, 'fixture refusal')
except nbt_native_cache.Refuse:
    pass
else:
    raise AssertionError('Refusal was not raised')
'''
        result = subprocess.run([sys.executable, '-c', code, str(script)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
