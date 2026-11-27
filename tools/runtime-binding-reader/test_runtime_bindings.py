import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runtime_binding_reader_under_test', HERE / 'nbt_runtime_bindings.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
BASES = {'hmi': 0, 'cpp': 0x78000000, 'qnx_cpp': 0x79000000, 'hmibase': 0x7a000000}


class Memory:
    def __init__(self):
        self.bytes = {}
        self.calls = 0
        self.total = 0
        self.closed = False
        self.reads = []
        self.counts = {}
        self.mutate_on_second = None
        self.short = False
        self.bases = {'hmi': 0, 'cpp': BASES['cpp'], 'plugin': 0x7b000000, 'remoting': 0x7c000000}
        self.header = ['libecpp-ne.so.4! @79000000 812K', 'libhmibase.so @7a000000 48K']

    def put(self, address, value):
        for i, byte in enumerate(value):
            self.bytes[address + i] = byte

    def word(self, address, value):
        self.put(address, struct.pack('<I', value))

    def read(self, address, size):
        self.reads.append((address, size))
        self.calls += 1
        self.total += ((address + size + 3) & ~3) - (address & ~3)
        self.counts[address] = self.counts.get(address, 0) + 1
        if address == self.mutate_on_second and self.counts[address] == 2:
            self.word(address, 0x12345678)
        value = bytes(self.bytes[address + i] for i in range(size))
        return value[:-1] if self.short else value

    def close(self):
        self.closed = True


def fixture():
    profile = json.loads((HERE / 'binding-layout.json').read_text())
    memory = Memory()
    seed = 1
    for key, module in profile['modules'].items():
        for fp in module['fingerprints']:
            value = bytes([seed]) * fp['bytes']
            seed += 1
            fp['sha256'] = hashlib.sha256(value).hexdigest()
            memory.put(BASES[key] + fp['offset'], value)
    definitions = {}
    for row in profile['definitions']:
        definitions[(row['module'], row['symbol'])] = BASES[row['module']] + row['offset']
    for row in profile['bindings']:
        name = row['symbol']
        candidates = [(m, name) for m in ('cpp', 'qnx_cpp', 'hmi') if (m, name) in definitions]
        memory.word(BASES[row['module']] + row['offset'], definitions[candidates[0]])
    for row in profile['definitions']:
        if row['symbol'] not in profile['stream_symbols']:
            continue
        vt = '_ZTVSt7istream' if row['symbol'] == '_ZSt3cin' else '_ZTVSt7ostream'
        if row['module'] in ('hmi', 'cpp'):
            vt = '_ZTVSi' if row['symbol'] == '_ZSt3cin' else '_ZTVSo'
            module = 'cpp'
        else:
            module = 'qnx_cpp'
        memory.word(BASES[row['module']] + row['offset'], definitions[(module, vt)] + 8)
    return profile, memory, definitions


class Bindings(unittest.TestCase):
    def test_profile_static_roster_and_copy_not_pointer(self):
        p = json.loads((HERE / 'binding-layout.json').read_text())
        reader.validate_profile(p, BASES)
        self.assertEqual(len(p['bindings']), 27)
        self.assertEqual(len(p['definitions']), 35)
        self.assertEqual(sum(len(m['fingerprints']) for m in p['modules'].values()), 5)
        self.assertFalse(any(r['relocation_type'] == 20 for r in p['bindings']))
        self.assertTrue(any(r['module'] == 'hmi' and r['symbol'] == '_ZSt4cerr'
                            and r['bytes'] == 140 for r in p['definitions']))

    def test_success_reports_bindings_and_distinct_stream_sizes(self):
        p, m, defs = fixture()
        r = reader.inspect_bindings(m, BASES, p)
        self.assertEqual(len(r['bindings']), 27)
        self.assertTrue(all(b['same_symbol_address_matches'] for b in r['bindings']))
        sizes = {(o['storage_module'], o['symbol']): o['declared_bytes'] for o in r['stream_storage']}
        self.assertEqual(sizes[('cpp', '_ZSt4cout')], 140)
        self.assertEqual(sizes[('qnx_cpp', '_ZSt4cout')], 52)
        self.assertFalse(r['ABI_compatibility_verified'])
        self.assertFalse(r['initialization_order_verified'])
        self.assertLessEqual(m.calls, reader.MAX_CALLS)
        self.assertLessEqual(m.total, reader.MAX_BYTES)
        self.assertEqual(r['observer_read_calls'], m.calls)
        self.assertEqual(r['observer_aligned_bytes'], m.total)

    def test_unknown_target_is_reported_without_dereferencing_it(self):
        p, m, _ = fixture()
        slot = p['bindings'][0]
        m.word(BASES[slot['module']] + slot['offset'], 0xdead0000)
        r = reader.inspect_bindings(m, BASES, p)
        self.assertEqual(r['bindings'][0]['target'], '0xdead0000')
        self.assertEqual(r['bindings'][0]['exact_named_address_matches'], [])
        self.assertFalse(any(a == 0xdead0000 for a, _ in m.reads))

    def test_zero_pointer_is_not_called_or_claimed_resolved(self):
        p, m, _ = fixture()
        slot = p['bindings'][0]
        m.word(BASES[slot['module']] + slot['offset'], 0)
        r = reader.inspect_bindings(m, BASES, p)
        self.assertEqual(r['bindings'][0]['target'], '0x0')
        self.assertEqual(r['bindings'][0]['same_symbol_address_matches'], [])
        self.assertFalse(any(a == 0 for a, _ in m.reads))

    def test_lazy_plt_pointer_is_identified_without_resolving_it(self):
        p, m, _ = fixture()
        slot = p['bindings'][0]
        address = BASES[slot['module']] + p['modules'][slot['module']]['plt_offset'] + 20
        m.word(BASES[slot['module']] + slot['offset'], address)
        r = reader.inspect_bindings(m, BASES, p)
        self.assertEqual(r['bindings'][0]['target_inside_captured_PLT'], [slot['module']])
        self.assertFalse(any(a == address for a, _ in m.reads))

    def test_fingerprint_mismatch_stops_before_slot_reads(self):
        p, m, _ = fixture()
        fp = p['modules']['hmi']['fingerprints'][0]
        m.put(fp['offset'], b'x' * fp['bytes'])
        with self.assertRaisesRegex(reader.Refuse, 'fingerprint mismatch'):
            reader.inspect_bindings(m, BASES, p)
        self.assertEqual(m.calls, 1)

    def test_changed_binding_is_refused(self):
        p, m, _ = fixture()
        slot = p['bindings'][0]
        m.mutate_on_second = BASES[slot['module']] + slot['offset']
        with self.assertRaisesRegex(reader.Refuse, 'Binding changed'):
            reader.inspect_bindings(m, BASES, p)

    def test_changed_stream_first_word_is_refused(self):
        p, m, defs = fixture()
        m.mutate_on_second = defs[('cpp', '_ZSt4cout')]
        with self.assertRaisesRegex(reader.Refuse, 'Stream first word changed'):
            reader.inspect_bindings(m, BASES, p)

    def test_short_read_is_refused(self):
        p, m, _ = fixture()
        m.short = True
        with self.assertRaisesRegex(reader.Refuse, 'Incomplete'):
            reader.inspect_bindings(m, BASES, p)

    def test_copy_relocation_cannot_be_read_as_pointer_slot(self):
        p, m, _ = fixture()
        p['bindings'][0]['relocation_type'] = 20
        with self.assertRaisesRegex(reader.Refuse, 'not a COPY'):
            reader.inspect_bindings(m, BASES, p)
        self.assertEqual(m.calls, 0)

    def test_bad_offsets_counts_and_bounds_stop_before_reads(self):
        for mutation in ('unaligned', 'outside_region', 'duplicate', 'too_many', 'bad_base', 'fingerprint_overflow'):
            with self.subTest(mutation=mutation):
                p, m, _ = fixture()
                bases = dict(BASES)
                if mutation == 'unaligned': p['bindings'][0]['offset'] += 1
                if mutation == 'outside_region': p['bindings'][0]['offset'] = 0
                if mutation == 'duplicate': p['bindings'].append(copy.deepcopy(p['bindings'][0]))
                if mutation == 'too_many': p['bindings'] *= 2
                if mutation == 'bad_base': bases['qnx_cpp'] = -1
                if mutation == 'fingerprint_overflow': p['modules']['cpp']['fingerprints'][0]['offset'] = 0x7fffffff
                with self.assertRaises(reader.Refuse): reader.inspect_bindings(m, bases, p)
                self.assertEqual(m.calls, 0)

    def test_budgets_are_enforced(self):
        for calls, size in ((1, 8192), (160, 1)):
            p, m, _ = fixture()
            with patch.object(reader, 'MAX_CALLS', calls), patch.object(reader, 'MAX_BYTES', size):
                with self.assertRaisesRegex(reader.Refuse, 'budget exceeded'):
                    reader.inspect_bindings(m, BASES, p)

    def test_mapping_formats_and_missing_conflicting_runtime(self):
        m = Memory()
        self.assertEqual(reader.parse_runtime_mappings(m.header, m.bases), BASES)
        for lines in (m.header[:1], m.header + ['libecpp-ne.so.4 @79900000']):
            with self.assertRaises(reader.Refuse): reader.parse_runtime_mappings(lines, m.bases)
        with self.assertRaises(reader.Refuse):
            reader.parse_runtime_mappings(m.header, dict(m.bases, hmi=0x100000))

    def test_main_mapping_only_never_reads_memory(self):
        m = Memory()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            path = Path(d) / 'mapping.json'
            rc = reader.main(['--pid', '294966', '--output', str(path)], lambda *_: m)
            r = json.loads(path.read_text())
        self.assertEqual(rc, 0)
        self.assertEqual(m.calls, 0)
        self.assertTrue(m.closed)
        self.assertNotIn('observation', r)

    def test_main_missing_mapping_records_stop_without_reads(self):
        m = Memory()
        m.header = []
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            path = Path(d) / 'stopped.json'
            rc = reader.main(['--pid', '294966', '--read-bindings', '--output', str(path)], lambda *_: m)
            r = json.loads(path.read_text())
        self.assertEqual(rc, 1)
        self.assertEqual(r['result'], 'stopped')
        self.assertEqual(m.calls, 0)
        self.assertTrue(m.closed)

    def test_main_does_not_overwrite_existing_file_or_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'keep.json'
            path.write_text('keep')
            dangling = Path(d) / 'dangling.json'
            dangling.symlink_to(Path(d) / 'absent')
            for output in (path, dangling):
                with self.assertRaisesRegex(reader.Refuse, 'already exists'):
                    reader.main(['--pid', '294966', '--output', str(output)],
                                lambda *_: self.fail('must not connect'))
            self.assertEqual(path.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
