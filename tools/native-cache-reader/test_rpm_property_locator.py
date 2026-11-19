import struct
import unittest
import json
from pathlib import Path

import nbt_native_cache as n
import rpm_property_locator as L

BASE = 0x10000000
REMOTING = 0x20000000
PROP_VT = REMOTING + L.LAYOUT_DEFAULTS['property_vtable']
CREATOR_VT = REMOTING + L.LAYOUT_DEFAULTS['creator_vtable']
LAYOUT = json.loads(Path(__file__).with_name('vehicle-layout.json').read_text())
PROXY = BASE + 0x10000
ENVIRONMENT = BASE + 0x1f000
VEHICLE = PROXY - LAYOUT['engine_speed_offset']


class Image:
    """Sparse little-endian memory image that also counts bounded reads."""
    def __init__(self):
        self.mem = bytearray(0x20000)
        self.top = 0x1000
        self.calls = 0
        self.total = 0
        self.mutate_after = None   # (call_number, address, bytes)

    def alloc(self, size, align=4):
        self.top = (self.top + align - 1) & ~(align - 1)
        addr = BASE + self.top
        self.top += size
        return addr

    def put(self, addr, data):
        self.mem[addr - BASE:addr - BASE + len(data)] = data

    def putw(self, addr, *words):
        self.put(addr, struct.pack('<%dI' % len(words), *words))

    def read(self, address, size):
        self.calls += 1
        self.total += size
        if self.mutate_after and self.calls == self.mutate_after[0]:
            self.put(self.mutate_after[1], self.mutate_after[2])
        n.require(BASE <= address and address + size <= BASE + len(self.mem), 'unmapped read %#x' % address)
        return bytes(self.mem[address - BASE:address - BASE + size])

    def cow(self, text):
        rep = self.alloc(12 + len(text) + 1)
        self.putw(rep, len(text), len(text), 1)
        self.put(rep + 12, text + b'\0')
        return rep + 12


def build(names, bound=False, handlers=0, root_override=None, bad_vtable=False, proxy=PROXY):
    img = Image()
    provider = img.alloc(0x100)
    img.putw(provider, REMOTING + LAYOUT['provider_vtable'])
    img.putw(provider + LAYOUT['environment_offset'], ENVIRONMENT)
    img.putw(ENVIRONMENT, REMOTING + LAYOUT['environment_vtable'], VEHICLE)
    img.putw(VEHICLE, LAYOUT['vehicle_vtable'])
    img.putw(PROXY, LAYOUT['engine_speed_vtable'])
    header = provider + 0x24
    props = {}
    prop = img.alloc(0x6c)
    creator = img.alloc(16)
    img.putw(creator, CREATOR_VT)
    img.putw(prop, 0xdeadbeef if bad_vtable else PROP_VT)
    img.putw(prop + 0x10, creator)
    img.put(prop + 0x14, b'\1')
    sent1, sent2 = prop + 0x1c, prop + 0x24
    img.putw(sent2, sent2, sent2)
    img.putw(prop + 0x60, ENVIRONMENT, proxy)
    if handlers:
        nodes = [img.alloc(12) for _ in range(handlers)]
        chain = [sent1] + nodes + [sent1]
        for i, nd in enumerate(nodes):
            img.putw(nd, chain[i + 2], chain[i], 0x03000000 + i * 0x100)
        img.putw(sent1, nodes[0], nodes[-1])
    else:
        img.putw(sent1, sent1, sent1)
    img.put(prop + 0x68, bytes([0, 1 if bound else 0]))

    nodes_by_key = {}
    def make(lo, hi, parent):
        if lo >= hi:
            return 0
        mid = (lo + hi) // 2
        node = img.alloc(0x18)
        nodes_by_key[names[mid]] = node
        key = img.cow(names[mid])
        value = prop if names[mid] == L.NAME else img.alloc(8)
        img.putw(node, 0, parent, make(lo, mid, node), make(mid + 1, hi, node), key, value)
        return node
    root = make(0, len(names), header) if names else 0
    left = nodes_by_key[names[0]] if names else header
    right = nodes_by_key[names[-1]] if names else header
    img.putw(header, 0, root if root_override is None else root_override, left, right, len(names))
    return img, provider, prop


def graph_for(img):
    return n.CacheGraph(img, {'remoting': REMOTING, 'plugin': 0, 'cpp': 0, 'hmi': 0}, LAYOUT)


NAMES = sorted([b'car.speed', b'engine.RPMSpeed', b'engine.temp', b'vehicle.fuel', b'aaa', b'zzz.last', b'engine.RPM', b'engine.RPMSpeedX'])


class LocatorTests(unittest.TestCase):
    def test_found_unbound(self):
        img, provider, prop = build(NAMES)
        r = L.inspect_rpm_property(graph_for(img), provider, expected_proxy=PROXY)
        self.assertTrue(r['property_found'])
        self.assertEqual(r['property_address'], hex(prop))
        self.assertFalse(r['bound_0x69']); self.assertFalse(r['subscribed_0x68'])
        self.assertEqual(r['handler_count'], 0)
        self.assertTrue(r['proxy_matches_cache_reader'])
        self.assertEqual(r['current_state'], 'no_current_bind_observed')
        self.assertFalse(r['binding_history_verified'])

    def test_found_bound_with_handlers(self):
        img, provider, prop = build(NAMES, bound=True, handlers=2)
        r = L.inspect_rpm_property(graph_for(img), provider)
        self.assertTrue(r['bound_0x69']); self.assertEqual(r['handler_count'], 2)
        self.assertEqual(r['handler_addresses'], ['0x3000000', '0x3000100'])
        self.assertEqual(r['current_state'], 'bound_with_handlers')
        self.assertIn('does not establish', r['interpretation'])

    def test_mixed_state_is_not_interpreted(self):
        img, provider, prop = build(NAMES, bound=True, handlers=0)
        r = L.inspect_rpm_property(graph_for(img), provider)
        self.assertIn('Mixed state', r['interpretation'])

    def test_absent_name_variants(self):
        for names in ([b'aaa', b'zzz.last'], [b'engine.RPMSpeedX'], [b'engine.RPM'], [b'a', b'engine.RPMSpee', b'z']):
            img, provider, _ = build(names)
            r = L.inspect_rpm_property(graph_for(img), provider)
            self.assertFalse(r['property_found'], names)

    def test_empty_map(self):
        img, provider, _ = build([])
        r = L.inspect_rpm_property(graph_for(img), provider)
        self.assertFalse(r['property_found']); self.assertEqual(r['map_node_count'], 0)

    def test_wrong_property_vtable_refused(self):
        img, provider, _ = build(NAMES, bad_vtable=True)
        with self.assertRaises(n.Refuse):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_proxy_mismatch_refused(self):
        img, provider, _ = build(NAMES)
        with self.assertRaisesRegex(n.Refuse, 'differs'):
            L.inspect_rpm_property(graph_for(img), provider, expected_proxy=0x0BADBAD0)

    def test_cycle_in_tree_refused(self):
        img, provider, _ = build(NAMES)
        root = struct.unpack_from('<I', img.mem, provider + 0x28 - BASE)[0]
        img.putw(root + 8, root)           # left child points to itself
        with self.assertRaises(n.Refuse):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_count_out_of_bounds_refused(self):
        img, provider, _ = build(NAMES)
        img.putw(provider + 0x34, 99999)
        with self.assertRaises(n.Refuse):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_handler_list_cycle_refused(self):
        img, provider, prop = build(NAMES, bound=True, handlers=2)
        first = struct.unpack_from('<I', img.mem, prop + 0x1c - BASE)[0]
        img.putw(first, first)             # next points to itself
        with self.assertRaises(n.Refuse):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_change_during_inspection_refused(self):
        img, provider, prop = build(NAMES)
        original = img.read
        def changing(address, size):
            result = original(address, size)
            if address == prop and size == 0x6c:
                img.put(prop + 0x69, b'\1')
            return result
        img.read = changing
        with self.assertRaises(n.Refuse):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_read_budget_is_small_and_bounded(self):
        img, provider, _ = build(NAMES)
        L.inspect_rpm_property(graph_for(img), provider)
        self.assertLess(img.calls, 100)
        self.assertLess(img.total, 8192)

    def test_only_reads_never_writes(self):
        img, provider, _ = build(NAMES)
        before = bytes(img.mem)
        L.inspect_rpm_property(graph_for(img), provider)
        self.assertEqual(before, bytes(img.mem))

    def test_long_key_needs_second_read(self):
        names = sorted(NAMES + [b'x' * 80])
        img, provider, _ = build(names)
        self.assertTrue(L.inspect_rpm_property(graph_for(img), provider)['property_found'])

    def test_key_at_mapping_boundary_needs_no_prefetch(self):
        img, provider, _ = build(NAMES)
        graph = graph_for(img)
        _, node, _ = L.lower_bound(graph, provider)
        key = BASE + len(img.mem) - len(L.NAME) - 1
        img.putw(key - 12, len(L.NAME), len(L.NAME), 1)
        img.put(key, L.NAME + b'\0')
        img.putw(node + 0x10, key)
        self.assertTrue(L.inspect_rpm_property(graph, provider)['property_found'])

    def test_tree_change_with_unchanged_header_refused(self):
        img, provider, _ = build(NAMES)
        root = struct.unpack_from('<I', img.mem, provider + 0x28 - BASE)[0]
        original = img.read
        def changing(address, size):
            result = original(address, size)
            if address == root and size == 0x18:
                img.putw(root, 1)
            return result
        img.read = changing
        with self.assertRaisesRegex(n.Refuse, 'changed'):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_handler_change_with_unchanged_sentinel_refused(self):
        img, provider, prop = build(NAMES, bound=True, handlers=1)
        first = struct.unpack_from('<I', img.mem, prop + 0x1c - BASE)[0]
        original = img.read
        def changing(address, size):
            result = original(address, size)
            if address == first and size == 12:
                img.putw(first + 8, 0x04000000)
            return result
        img.read = changing
        with self.assertRaisesRegex(n.Refuse, 'changed'):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_property_environment_mismatch_refused(self):
        img, provider, prop = build(NAMES)
        img.putw(prop + 0x60, ENVIRONMENT + 4)
        with self.assertRaisesRegex(n.Refuse, 'environment/proxy'):
            L.inspect_rpm_property(graph_for(img), provider)

    def test_wrong_tree_parent_refused(self):
        img, provider, _ = build(NAMES)
        root = struct.unpack_from('<I', img.mem, provider + 0x28 - BASE)[0]
        img.putw(root + 4, root)
        with self.assertRaisesRegex(n.Refuse, 'parent'):
            L.inspect_rpm_property(graph_for(img), provider)


class RequestStateTests(unittest.TestCase):
    def make(self, state, host_null=False):
        img = Image()
        proxy = img.alloc(0x80)
        host = img.alloc(0x80)
        img.putw(proxy, LAYOUT['engine_speed_vtable'])
        img.putw(host, LAYOUT['vehicle_vtable'])
        img.putw(proxy + 0x10, 0 if host_null else host)
        img.put(proxy + 0x18, struct.pack('<H', 0x2c1))
        img.put(proxy + 0x60, b'\0')
        img.putw(host + 0x58, state)
        img.put(host + 0x34, struct.pack('<H', 0x1234))
        img.put(host + 0x36, bytes([0x56, 7]))
        return img, proxy

    def test_state_two_passes_only_early_gate(self):
        img, proxy = self.make(2)
        r = L.inspect_request_state(graph_for(img), proxy)
        self.assertEqual(r['host_state_0x58'], 2)
        self.assertEqual((r['device_address_0x34'], r['fblock_id_0x36'],
                          r['instance_id_0x37'], r['function_id_0x18']),
                         (0x1234, 0x56, 7, 0x2c1))
        self.assertTrue(r['state_gate_eligible'])
        self.assertFalse(r['transmission_verified'])

    def test_other_state_sends_nothing(self):
        img, proxy = self.make(1)
        self.assertFalse(L.inspect_request_state(graph_for(img), proxy)['state_gate_eligible'])

    def test_null_host(self):
        img, proxy = self.make(0, host_null=True)
        self.assertIn('error 4', L.inspect_request_state(graph_for(img), proxy)['request_gate'])

    def test_implausible_state_refused(self):
        img, proxy = self.make(0x12345678)
        with self.assertRaises(n.Refuse):
            L.inspect_request_state(graph_for(img), proxy)

    def test_host_state_change_without_proxy_change_refused(self):
        img, proxy = self.make(2)
        host = struct.unpack_from('<I', img.mem, proxy + 0x10 - BASE)[0]
        original = img.read
        def changing(address, size):
            result = original(address, size)
            if address == host + 0x30 and size == 0x2c:
                img.putw(host + 0x58, 1)
            return result
        img.read = changing
        with self.assertRaisesRegex(n.Refuse, 'changed'):
            L.inspect_request_state(graph_for(img), proxy)

    def test_null_host_result_still_rechecks_proxy(self):
        img, proxy = self.make(0, host_null=True)
        original = img.read
        def changing(address, size):
            result = original(address, size)
            if address == proxy and size == 0x70:
                img.putw(proxy + 0x10, BASE + 0x1080)
            return result
        img.read = changing
        with self.assertRaisesRegex(n.Refuse, 'changed'):
            L.inspect_request_state(graph_for(img), proxy)

    def test_wrong_host_type_refused(self):
        img, proxy = self.make(2)
        host = struct.unpack_from('<I', img.mem, proxy + 0x10 - BASE)[0]
        img.putw(host, 0xdeadbeef)
        with self.assertRaisesRegex(n.Refuse, 'vehicle function block'):
            L.inspect_request_state(graph_for(img), proxy)


if __name__ == '__main__':
    unittest.main()
