import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest

from app_admission import inspect_admission
from nbt_native_cache import CacheGraph, Refuse, fnv1a
from test_native_cache import BASES, LAYOUT, fixture


PROFILE = json.loads(Path(__file__).with_name('admission-layout.json').read_text())
CODING = 0x73000000
SERVER = 0x2030000
BUCKETS = 0x2050000
NODE = 0x2050100
BUFFER = 0x2040000


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.memory, self.old = fixture()
        self.layout = copy.deepcopy(PROFILE)
        # Fixture bytes validate the fingerprint guard without embedding firmware.
        self.layout['fingerprints'] = [
            {'module': 'coding', 'offset': 0x100, 'bytes': 4,
             'sha256': hashlib.sha256(b'TEST').hexdigest()}]
        self.memory.add(CODING + 0x100, 4)
        self.memory.put(CODING + 0x100, b'TEST')
        self.bases = dict(BASES, coding=CODING)
        self.graph = CacheGraph(self.memory, self.bases, LAYOUT)
        name = b'IHmiVariantServer'
        self.memory.words(self.old['key'] - 12, len(name))
        self.memory.put(self.old['key'], name + b'\0')
        self.memory.put(self.old['buckets'], bytes(32))
        self.memory.words(self.old['buckets'] + (fnv1a(name) % 7) * 4, self.old['node'])
        self.memory.words(self.old['tls'] + 8, SERVER)
        self.memory.add(SERVER, 0x3400)
        self.memory.words(SERVER, CODING + PROFILE['variant_vtable'], 0)
        self.memory.add(BUCKETS, 32)
        self.memory.add(NODE, 12)
        feature = PROFILE['direct_feature']
        self.descriptor = CODING + feature['descriptor_offset']
        self.memory.add(self.descriptor, 36)
        self.memory.add(BUFFER, 256)
        self.memory.words(SERVER + PROFILE['va_map_offset'] + 8, BUCKETS, 7, 1)
        self.memory.words(BUCKETS + feature['id'] % 7 * 4, NODE)
        self.memory.words(NODE, feature['id'], self.descriptor, 0)
        block = bytearray(36)
        for offset, value in [(8, feature['page']), (0xa, feature['byte_offset']),
                              (0xe, feature['extra_offset']), (0x20, 256)]:
            struct.pack_into('<H', block, offset, value)
        block[0x10], block[0x11] = feature['mask'], feature['expected_value']
        struct.pack_into('<III', block, 0x14, feature['id'],
                         CODING + feature['name_offset'], BUFFER)
        self.memory.put(self.descriptor, block)
        for key in PROFILE['iva_features']:
            self.iva(key, False)

    def iva_address(self, key):
        feature = PROFILE['iva_features'][key]
        return SERVER + PROFILE['iva_array_offset'] + (feature - PROFILE['iva_origin']) * 8

    def iva(self, key, enabled):
        self.memory.words(self.iva_address(key), PROFILE['iva_features'][key], int(enabled))

    def result(self):
        return inspect_admission(self.graph, self.layout)

    def test_all_predicates_false_without_claiming_app_manager_scope(self):
        report = self.result()
        self.assertFalse(report['instances'][0]['predicate_for_this_instance'])
        self.assertFalse(report['app_manager_scope_association_verified'])
        self.assertFalse(report['plugin_loading_verified'])

    def test_direct_remote_apps_bit_permits_this_predicate(self):
        self.memory.put(BUFFER + PROFILE['direct_feature']['byte_offset'], b'\1')
        report = self.result()['instances'][0]
        self.assertTrue(report['direct_1a0']['native_predicate_result'])
        self.assertTrue(report['predicate_for_this_instance'])

    def test_each_general_iva_route_independently_permits_predicate(self):
        for key in ('remote_hmi', 'apps', 'touch_command'):
            with self.subTest(route=key):
                self.iva(key, True)
                self.assertTrue(self.result()['instances'][0]['derived_9c56'])
                self.iva(key, False)

    def test_special_vehicle_route_requires_role_one(self):
        self.iva('special_security', True)
        self.assertFalse(self.result()['instances'][0]['derived_9c55'])
        self.memory.words(SERVER + 4, 1)
        self.assertTrue(self.result()['instances'][0]['derived_9c55'])

    def test_empty_iva_entry_is_not_mistaken_for_a_true_entry(self):
        self.memory.words(self.iva_address('apps'), 0, 1)
        instance = self.result()['instances'][0]
        self.assertFalse(instance['cached_iva']['apps']['native_predicate_result'])
        self.assertFalse(instance['cached_iva']['apps']['entry_populated'])

    def test_missing_va_entry_is_distinguished_from_a_selected_zero(self):
        self.memory.put(BUCKETS, bytes(32))
        result = self.result()['instances'][0]['direct_1a0']
        self.assertFalse(result['coding_data_available'])
        self.assertIn('absent/null', result['reason'])

    def test_missing_coding_buffer_is_reported_without_a_buffer_read(self):
        self.memory.words(self.descriptor + 0x1c, 0)
        result = self.result()['instances'][0]['direct_1a0']
        self.assertFalse(result['coding_data_available'])
        self.assertFalse(any(address == BUFFER for address, _ in self.memory.reads))

    def test_short_coding_buffer_is_not_dereferenced(self):
        self.memory.put(self.descriptor + 0x20, struct.pack('<H', 1))
        self.assertFalse(self.result()['instances'][0]['direct_1a0']['coding_data_available'])

    def test_wrong_descriptor_is_refused(self):
        self.memory.words(NODE + 4, self.descriptor + 4)
        with self.assertRaisesRegex(Refuse, 'descriptor'):
            self.result()

    def test_changed_mask_is_refused(self):
        self.memory.put(self.descriptor + 0x10, b'\2')
        with self.assertRaisesRegex(Refuse, 'layout'):
            self.result()

    def test_wrong_variant_server_type_is_refused(self):
        self.memory.words(SERVER, 0x12340000)
        with self.assertRaisesRegex(Refuse, 'variant server'):
            self.result()

    def test_wrong_cached_iva_identity_is_refused(self):
        self.memory.words(self.iva_address('apps'), 999, 1)
        with self.assertRaisesRegex(Refuse, 'IVA'):
            self.result()

    def test_coding_buffer_change_is_refused(self):
        target = BUFFER + PROFILE['direct_feature']['byte_offset']
        original = self.memory.read
        def changing(address, size):
            value = original(address, size)
            if address == target:
                self.memory.put(target, b'\1')
            return value
        self.memory.read = changing
        with self.assertRaisesRegex(Refuse, 'changed'):
            self.result()

    def test_coding_map_cycle_is_refused(self):
        self.memory.words(NODE, 999, self.descriptor, NODE)
        with self.assertRaisesRegex(Refuse, 'cycle'):
            self.result()

    def test_missing_module_mapping_stops_before_any_read(self):
        del self.graph.bases['coding']
        with self.assertRaisesRegex(Refuse, 'mapping'):
            self.result()
        self.assertEqual(self.memory.reads, [])

    def test_wrong_code_stops_before_registry_lookup(self):
        self.memory.put(CODING + 0x100, b'FAIL')
        with self.assertRaisesRegex(Refuse, 'fingerprint'):
            self.result()
        self.assertEqual(self.memory.reads, [(CODING + 0x100, 4)])

    def test_inspection_changes_no_fixture_memory(self):
        before = {address: bytes(data) for address, data in self.memory.parts.items()}
        self.result()
        self.assertEqual(before, {address: bytes(data) for address, data in self.memory.parts.items()})


if __name__ == '__main__':
    unittest.main()
