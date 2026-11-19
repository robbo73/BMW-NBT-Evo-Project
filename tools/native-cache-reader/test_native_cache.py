import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from nbt_native_cache import CacheGraph, Refuse, SSHMemory, fnv1a, parse_header


LAYOUT = json.loads(Path(__file__).with_name('vehicle-layout.json').read_text())
BASES = {'plugin': 0x70000000, 'remoting': 0x71000000, 'cpp': 0x72000000, 'hmi': 0}


class Memory:
    def __init__(self):
        self.parts = {}
        self.reads = []

    def add(self, address, size):
        self.parts[address] = bytearray(size)

    def put(self, address, data):
        for start, part in self.parts.items():
            if start <= address and address + len(data) <= start + len(part):
                part[address-start:address-start+len(data)] = data
                return
        raise AssertionError(hex(address))

    def words(self, address, *values):
        self.put(address, struct.pack('<' + 'I' * len(values), *values))

    def read(self, address, size):
        self.reads.append((address, size))
        for start, part in self.parts.items():
            if start <= address and address + size <= start + len(part):
                return bytes(part[address-start:address-start+size])
        raise Refuse('Fixture refuses an unmodelled address: %#x' % address)


def fixture():
    memory = Memory()
    root = BASES['plugin'] + LAYOUT['registry_offset']
    memory.add(root, 20)
    buckets, node, key = 0x2000000, 0x2000100, 0x2000200
    cache, scopes, scope_node, tls = 0x2000300, 0x2000400, 0x2000500, 0x2000600
    provider, environment, vehicle = 0x2000700, 0x2000800, 0x2010000
    for address, size in [(buckets, 32), (node, 12), (key-12, 80), (cache, 48),
                          (scopes, 16), (scope_node, 12), (tls, 12),
                          (provider, 32), (environment, 8), (vehicle, 0x5000)]:
        memory.add(address, size)
    memory.words(root+8, buckets, 7, 1)
    memory.words(buckets + (fnv1a(b'ICarDataServer') % 7)*4, node)
    memory.words(node, key, cache, 0)
    memory.words(key-12, 14)
    memory.put(key, b'ICarDataServer\0')
    memory.words(cache, BASES['plugin'] + LAYOUT['cache_vtable'])
    memory.words(cache+0x18, scopes, 3, 1)
    memory.words(scopes, scope_node)
    memory.words(scope_node, 0x123400, tls, 0)
    memory.words(tls, BASES['plugin']+LAYOUT['tls_vtable'], 0, provider)
    memory.words(provider, BASES['remoting']+LAYOUT['provider_vtable'])
    memory.words(provider+LAYOUT['environment_offset'], environment)
    memory.words(environment, BASES['remoting']+LAYOUT['environment_vtable'], vehicle)
    memory.words(vehicle, LAYOUT['vehicle_vtable'])
    speed = vehicle + LAYOUT['engine_speed_offset']
    memory.words(speed, LAYOUT['engine_speed_vtable'])
    memory.words(speed+LAYOUT['registration_offset'], 1)
    memory.put(speed+LAYOUT['valid_offset'], b'\1')
    memory.put(speed+LAYOUT['raw_offset'], struct.pack('<H', 3200))
    return memory, locals()


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.memory, self.address = fixture()
        self.graph = CacheGraph(self.memory, BASES, LAYOUT)

    def test_existing_cache_to_native_rpm(self):
        cache = self.graph.find_cache()
        scopes = self.graph.scope_providers(cache)
        self.assertEqual(len(scopes), 1)
        _, tls, provider = scopes[0]
        result = self.graph.sample(tls, provider)
        self.assertEqual((result['raw_u16'], result['cached_rpm']), (3200, 800))
        self.assertEqual(result['freshness'], 'unverified')

    def test_changed_samples_are_not_claimed_as_fresh(self):
        results = []
        for raw in [3200, 12000, 12004]:
            self.memory.put(self.address['speed']+LAYOUT['raw_offset'], struct.pack('<H', raw))
            results.append(self.graph.sample(self.address['tls'], self.address['provider']))
        self.assertEqual([x['cached_rpm'] for x in results], [800, 3000, 3001])
        self.assertTrue(all(x['freshness'] == 'unverified' for x in results))

    def test_special_invalid_and_out_of_range(self):
        for raw in [65535, 65534]:
            self.memory.put(self.address['speed']+LAYOUT['raw_offset'], struct.pack('<H', raw))
            self.assertIsNone(self.graph.sample(self.address['tls'], self.address['provider'])['cached_rpm'])

    def test_invalid_status_is_not_rpm(self):
        self.memory.put(self.address['speed']+LAYOUT['valid_offset'], b'\0')
        self.assertIsNone(self.graph.sample(self.address['tls'], self.address['provider'])['cached_rpm'])

    def test_missing_registration_is_not_rpm(self):
        self.memory.words(self.address['speed']+LAYOUT['registration_offset'], 0)
        self.assertIsNone(self.graph.sample(self.address['tls'], self.address['provider'])['cached_rpm'])

    def test_registry_changes_during_lookup_stop(self):
        read = self.memory.read
        seen = []
        def changing(address, size):
            if address == self.address['root']:
                if seen:
                    self.memory.words(address+16, 2)
                seen.append(1)
            return read(address, size)
        self.memory.read = changing
        with self.assertRaisesRegex(Refuse, 'Registry changed'):
            self.graph.find_cache()

    def test_environment_changes_during_sample_stop(self):
        read = self.memory.read
        seen = []
        target = self.address['provider']+LAYOUT['environment_offset']
        def changing(address, size):
            if address == target:
                if seen:
                    self.memory.words(address, 0)
                seen.append(1)
            return read(address, size)
        self.memory.read = changing
        with self.assertRaises(Refuse):
            self.graph.sample(self.address['tls'], self.address['provider'])

    def test_cache_absent_does_not_create_one(self):
        self.memory.words(self.address['buckets']+(fnv1a(b'ICarDataServer') % 7)*4, 0)
        with self.assertRaisesRegex(Refuse, 'not present'):
            self.graph.find_cache()

    def test_registry_cycle_stops(self):
        self.memory.put(self.address['key'], b'WrongInterface\0')
        self.memory.words(self.address['node']+8, self.address['node'])
        with self.assertRaisesRegex(Refuse, 'cycle'):
            self.graph.find_cache()

    def test_registry_bound_stops_before_buckets(self):
        self.memory.words(self.address['root']+12, 0x7fffffff)
        with self.assertRaisesRegex(Refuse, 'bounds'):
            self.graph.find_cache()
        self.assertEqual(len(self.memory.reads), 1)

    def test_bad_cache_vtable_stops(self):
        self.memory.words(self.address['cache'], 0x12345678)
        with self.assertRaisesRegex(Refuse, 'vtable'):
            self.graph.find_cache()

    def test_scope_cycle_stops(self):
        self.memory.words(self.address['scope_node']+8, self.address['scope_node'])
        with self.assertRaisesRegex(Refuse, 'cycle'):
            self.graph.scope_providers(self.address['cache'])

    def test_scope_count_inconsistency_stops(self):
        self.memory.words(self.address['cache']+0x20, 2)
        with self.assertRaisesRegex(Refuse, 'count inconsistent'):
            self.graph.scope_providers(self.address['cache'])

    def test_no_cached_provider_does_not_initialize(self):
        self.memory.words(self.address['tls']+8, 0)
        with self.assertRaisesRegex(Refuse, 'No existing scope'):
            self.graph.scope_providers(self.address['cache'])

    def test_null_environment_stops(self):
        self.memory.words(self.address['provider']+LAYOUT['environment_offset'], 0)
        with self.assertRaisesRegex(Refuse, 'Invalid'):
            self.graph.sample(self.address['tls'], self.address['provider'])

    def test_unexpected_vehicle_type_stops(self):
        self.memory.words(self.address['vehicle'], 0x12345678)
        with self.assertRaisesRegex(Refuse, 'vehicle proxy vtable'):
            self.graph.sample(self.address['tls'], self.address['provider'])

    def test_changed_provider_stops(self):
        self.memory.words(self.address['tls']+8, self.address['provider']+4)
        with self.assertRaisesRegex(Refuse, 'changed before'):
            self.graph.sample(self.address['tls'], self.address['provider'])

    def test_short_read_stops(self):
        self.memory.read = lambda address, size: b'\0'
        with self.assertRaisesRegex(Refuse, 'Incomplete'):
            self.graph.find_cache()

    def test_wrong_build_stops_before_pointer_walk(self):
        self.memory.add(0x100000, 64)
        with self.assertRaisesRegex(Refuse, 'fingerprint'):
            self.graph.verify_images()
        self.assertEqual(self.memory.reads, [(0x100000, 64)])


class TransportTests(unittest.TestCase):
    def test_startup_failure_reports_phase_exit_status_and_output(self):
        peer = subprocess.Popen(
            [sys.executable, '-c',
             "import sys; print('278582 /opt/hmi/bin/zipped/HmiMain3D -c'); sys.exit(3)"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        with patch('nbt_native_cache.subprocess.Popen', return_value=peer):
            with self.assertRaisesRegex(
                    Refuse, 'mapping startup; SSH exit status: 3; last startup output: 278582'):
                SSHMemory('root@192.168.16.101', 278582)

    def test_generated_native_command_with_full_mapping_output(self):
        # Execute the actual generated shell command with fake native utilities.
        # This covers quoting and startup framing as well as >32 pidin lines.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            utilities = {
                'on': '#!/bin/sh\nshift 2\nexec "$@"\n',
                'pidin': '''#!/bin/sh
if [ "$3" = ar ]; then
    echo '278582 /opt/hmi/bin/zipped/HmiMain3D -c'
else
    index=0
    while [ "$index" -lt 70 ]; do
        echo '278582 1 HmiMain3D CONDVAR'
        index=$((index+1))
    done
    echo 'libhmiplugin.so @70000000 200K 4K'
    echo 'libhmiremoting.so! @71000000 6768K 248K'
    echo 'libstdc++.so.6 @72000000 812K 48K'
fi
''',
                'dd': '#!/bin/sh\nexec /bin/dd if=/dev/zero "$@"\n',
            }
            for name, body in utilities.items():
                path = root/name
                path.write_text(body)
                path.chmod(0o755)
            popen = subprocess.Popen
            def spawn(argv, **kwargs):
                # Mapping mode never invokes dd; stdin remains a request pipe.
                return popen(['/bin/sh', '-c', argv[-1]],
                             env=dict(os.environ, PATH=directory+':'+os.environ['PATH']),
                             **kwargs)
            with patch('nbt_native_cache.subprocess.Popen', side_effect=spawn):
                reader = SSHMemory('root@192.168.16.101', 278582)
            self.assertEqual(reader.bases, BASES)
            self.assertGreater(len(reader.header), 32)
            self.assertEqual((reader.total, reader.calls), (0, 0))
            reader.close()
            self.assertEqual(reader.process.returncode, 0)

    def test_pipe_protocol_preserves_binary_and_closes_without_reads(self):
        # Real OS pipes and a fake native peer; no network or target code runs.
        server = '''import os, sys
header = b"278582 /opt/hmi/bin/zipped/HmiMain3D -c\\nlibhmiplugin.so @70000000 200K 4K\\nlibhmiremoting.so! @71000000 6768K 248K\\nlibstdc++.so.6 @72000000 812K 48K\\nNBT_CACHE_READ_READY\\n"
for byte in header:
    os.write(1, bytes([byte]))
for line in sys.stdin.buffer:
    skip, count = map(int, line.split())
    os.write(1, b"\\x00\\xff\\n\\x80" * count)
'''
        for do_read in [False, True]:
            peer = subprocess.Popen([sys.executable, '-u', '-c', server],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            with patch('nbt_native_cache.subprocess.Popen', return_value=peer) as spawn:
                reader = SSHMemory('root@192.168.16.101', 278582)
            self.assertEqual(reader.bases, BASES)
            self.assertIn('on -f hu-omap', spawn.call_args[0][0][-1])
            if do_read:
                self.assertEqual(reader.read(0x10001, 7), b'\xff\n\x80\x00\xff\n\x80')
            else:
                self.assertEqual((reader.total, reader.calls), (0, 0))
            reader.close()
            self.assertEqual(peer.returncode, 0)

    def test_pipe_eof_and_deadline_stop(self):
        peer = subprocess.Popen([sys.executable, '-c', 'pass'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        reader = SSHMemory.__new__(SSHMemory)
        reader.process = peer
        try:
            with self.assertRaisesRegex(Refuse, 'SSH closed during output read'):
                reader._exact(4, time.monotonic() + 5)
            with self.assertRaisesRegex(Refuse, 'Timed out'):
                reader._exact(4, time.monotonic() - 1)
        finally:
            reader.close()

    def test_native_headers(self):
        lines = ['278582 /opt/hmi/bin/zipped/HmiMain3D -c -ro -rw',
                 'libhmiplugin.so @70000000 200K 4K',
                 'libhmiremoting.so! @71000000 6768K 248K',
                 'libstdc++.so.6 @72000000 812K 48K']
        self.assertEqual(parse_header(lines, 278582), BASES)
        with self.assertRaisesRegex(Refuse, 'PID'):
            parse_header(lines, 278583)
        with self.assertRaisesRegex(Refuse, 'All required'):
            parse_header(lines[:2], 278582)
        with self.assertRaisesRegex(Refuse, 'Conflicting'):
            parse_header(lines+['libhmiplugin.so @72000000'], 278582)

    def test_fnv_ascii_matches_known_vector(self):
        self.assertEqual(fnv1a(b'hello'), 0x4f9f2cab)

    def test_reads_are_aligned_and_bounded(self):
        reader = SSHMemory.__new__(SSHMemory)
        reader.process = type('Process', (), {'stdin': io.BytesIO()})()
        reader.total, reader.calls = 0, 0
        reader._exact = lambda count, deadline: bytes(range(count))
        self.assertEqual(reader.read(0x10001, 7), bytes(range(1, 8)))
        self.assertEqual(reader.process.stdin.getvalue(), b'16384 2\n')
        with self.assertRaisesRegex(Refuse, 'bounded'):
            reader.read(0, 4)
        reader.total = 262144
        with self.assertRaisesRegex(Refuse, 'budget'):
            reader.read(0x10000, 4)


if __name__ == '__main__':
    unittest.main()
