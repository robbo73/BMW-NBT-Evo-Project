#!/usr/bin/env python3
"""Observe existing HMI runtime pointer slots over SSH; no target code loading."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

# The same previously vehicle-tested transport, frozen into ready packages.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native-cache-reader'))
from nbt_native_cache import SSHMemory, Refuse, pointer, require

MODULES = {'hmi', 'cpp', 'qnx_cpp', 'hmibase'}
MAX_CALLS = 160
MAX_BYTES = 8192


def parse_runtime_mappings(lines, existing_bases):
    bases = {'hmi': existing_bases['hmi'], 'cpp': existing_bases['cpp']}
    require(bases['hmi'] == 0, 'Expected fixed-address HMI')
    for line in lines:
        match = re.search(r'\b(libecpp-ne\.so\.4|libhmibase\.so)[!*\s]*@([0-9a-fA-F]+)\b', line)
        if match:
            key = 'qnx_cpp' if match[1] == 'libecpp-ne.so.4' else 'hmibase'
            value = pointer(int(match[2], 16))
            require(key not in bases or bases[key] == value, 'Conflicting ' + key + ' mappings')
            bases[key] = value
    require(set(bases) == MODULES,
            'Required stock mappings missing: ' + ', '.join(sorted(MODULES - set(bases))))
    require(len({bases[k] for k in MODULES if k != 'hmi'}) == 3,
            'Conflicting runtime base addresses')
    return bases


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, 'Invalid ' + label)
    return value


def in_writable(module, offset, size):
    return any(r['offset'] <= offset and offset + size <= r['offset'] + r['bytes']
               for r in module['writable_regions'])


def validate_profile(profile, bases):
    require(profile['format'] == 'nbt-runtime-binding-profile/1', 'Unsupported binding profile')
    require(set(profile['modules']) == MODULES and set(bases) == MODULES,
            'Unexpected profile modules')
    for key, module in profile['modules'].items():
        integer(bases[key], 0 if key == 'hmi' else 0x10000, 0xfeffffff, 'module base')
        require(bases[key] % 4 == 0, 'Unaligned module base')
        require(module['elf_type'] == ('ET_EXEC' if key == 'hmi' else 'ET_DYN'),
                'Unexpected ELF load model')
        require(1 <= len(module['fingerprints']) <= 3, 'Unexpected fingerprint count')
        integer(module['plt_offset'], 0, 0xffffff, 'PLT offset')
        integer(module['plt_bytes'], 1, 0x100000, 'PLT length')
        require(1 <= len(module['readable_regions']) <= 4, 'Unexpected load regions')
        for region in module['readable_regions']:
            integer(region['offset'], 0, 0x7fffffff, 'load offset')
            integer(region['bytes'], 1, 0x10000000, 'load size')
            integer(region['file_bytes'], 1, region['bytes'], 'file-backed size')
            require(bases[key] + region['offset'] + region['bytes'] < 0xff000000,
                    'Load region outside process bounds')
        require(1 <= len(module['writable_regions']) <= 4, 'Unexpected writable regions')
        for region in module['writable_regions']:
            integer(region['offset'], 0, 0x7fffffff, 'region offset')
            integer(region['bytes'], 1, 0x10000000, 'region size')
            require(bases[key] + region['offset'] + region['bytes'] < 0xff000000,
                    'Region outside process bounds')
        for fp in module['fingerprints']:
            integer(fp['offset'], 0x100 if key != 'hmi' else 0x100000,
                    0x7fffffff, 'fingerprint offset')
            integer(fp['bytes'], 4, 128, 'fingerprint length')
            require(bases[key] + fp['offset'] + fp['bytes'] < 0xff000000,
                    'Fingerprint outside process bounds')
            require(any(r['offset'] <= fp['offset'] and fp['offset'] + fp['bytes']
                        <= r['offset'] + r['file_bytes'] for r in module['readable_regions']),
                    'Fingerprint outside captured file-backed load regions')
            require(re.fullmatch('[0-9a-f]{64}', fp['sha256']) is not None,
                    'Invalid fingerprint digest')
    require(1 <= len(profile['bindings']) <= 40, 'Unexpected binding count')
    require(1 <= len(profile['definitions']) <= 64, 'Unexpected definition count')
    seen = set()
    for row in profile['bindings']:
        key, offset = row['module'], row['offset']
        require(key in MODULES, 'Unknown binding module')
        integer(offset, 0, 0x7fffffff, 'binding offset')
        require(offset % 4 == 0 and row['relocation_type'] in (21, 22),
                'Expected aligned ARM pointer relocation, not a COPY object')
        require((key, offset) not in seen, 'Duplicate binding slot')
        require(in_writable(profile['modules'][key], offset, 4),
                'Binding outside captured writable region')
        require(isinstance(row['symbol'], str) and row['symbol'].startswith('_Z'),
                'Unexpected observed symbol')
        seen.add((key, offset))
    for row in profile['definitions']:
        require(row['module'] in MODULES, 'Unknown definition module')
        integer(row['offset'], 0, 0x7fffffff, 'definition offset')
        require(bases[row['module']] + row['offset'] < 0xff000000,
                'Definition outside process bounds')
        integer(row['bytes'], 1, 0x100000, 'symbol length')
        require(any(r['offset'] <= row['offset'] and row['offset'] + row['bytes']
                    <= r['offset'] + r['bytes']
                    for r in profile['modules'][row['module']]['readable_regions']),
                'Definition outside captured load regions')
        if row['symbol'] in profile['stream_symbols']:
            require(row['type'] == 'STT_OBJECT' and row['bytes'] >= 4
                    and row['offset'] % 4 == 0
                    and in_writable(profile['modules'][row['module']], row['offset'], 4),
                    'Stream definition outside writable storage')


def inspect_bindings(memory, bases, profile):
    validate_profile(profile, bases)
    calls, total = 0, 0

    def read(address, size):
        nonlocal calls, total
        require(0x10000 <= address and address + size < 0xff000000,
                'Observation outside user memory')
        aligned_size = ((address + size + 3) & ~3) - (address & ~3)
        calls += 1
        total += aligned_size
        require(calls <= MAX_CALLS and total <= MAX_BYTES, 'Binding observation budget exceeded')
        value = memory.read(address, size)
        require(len(value) == size, 'Incomplete binding observation')
        return value

    def word(address):
        return struct.unpack('<I', read(address, 4))[0]

    def fingerprints():
        for key, module in profile['modules'].items():
            for check in module['fingerprints']:
                value = read(bases[key] + check['offset'], check['bytes'])
                require(hashlib.sha256(value).hexdigest() == check['sha256'],
                        'Code/header fingerprint mismatch for ' + key)

    fingerprints()
    index, vtables = {}, {}
    for row in profile['definitions']:
        address = bases[row['module']] + row['offset']
        item = {'module': row['module'], 'symbol': row['symbol'],
                'bytes': row['bytes'], 'type': row['type']}
        index.setdefault(address, []).append(item)
        if row['symbol'].startswith('_ZTV'):
            vtables.setdefault(address + 8, []).append(item)
    slots, original_slots = [], []
    for row in profile['bindings']:
        address = bases[row['module']] + row['offset']
        target = word(address)
        matches = index.get(target, [])
        trampoline = [key for key, module in profile['modules'].items()
                      if bases[key] + module['plt_offset'] <= target
                      < bases[key] + module['plt_offset'] + module['plt_bytes']]
        slots.append({'module': row['module'], 'symbol': row['symbol'],
                      'relocation_type': row['relocation_type'],
                      'slot_address': hex(address), 'target': hex(target),
                      'exact_named_address_matches': matches,
                      'same_symbol_address_matches': [m for m in matches if m['symbol'] == row['symbol']],
                      'target_inside_captured_PLT': trampoline,
                      'interpretation': 'Observed pointer value; a PLT target may still be a trampoline. No target was invoked.'})
        original_slots.append((address, target))
    streams, original_streams = [], []
    for row in profile['definitions']:
        if row['symbol'] not in profile['stream_symbols']:
            continue
        address = bases[row['module']] + row['offset']
        first = word(address)
        streams.append({'storage_module': row['module'], 'symbol': row['symbol'],
                        'storage_address': hex(address), 'declared_bytes': row['bytes'],
                        'first_word': hex(first),
                        'exact_vtable_plus_8_matches': vtables.get(first, []),
                        'interpretation': 'First word only; not an ABI-validity or construction-history check.'})
        original_streams.append((address, first))
    for address, target in original_slots:
        require(word(address) == target, 'Binding changed during snapshot; preserve stopped report')
    for address, first in original_streams:
        require(word(address) == first, 'Stream first word changed during snapshot')
    fingerprints()
    return {'bindings': slots, 'stream_storage': streams,
            'snapshot_consistency': 'best_effort_rechecked_not_atomic',
            'observer_read_calls': calls, 'observer_aligned_bytes': total,
            'scope': 'Selected existing HMI bindings/storage only; not complete process symbol resolution.',
            'initialization_order_verified': False, 'ABI_compatibility_verified': False,
            'plugin_execution_verified': False}


def main(argv=None, memory_factory=SSHMemory):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', required=True, type=int, help='Fresh HmiMain3D PID on hu-omap')
    parser.add_argument('--target', default='root@192.168.16.101')
    parser.add_argument('--read-bindings', action='store_true',
                        help='Read fingerprinted existing binding slots; default is mappings only')
    parser.add_argument('--output', type=Path, required=True, help='New local JSON path')
    args = parser.parse_args(argv)
    require(not args.output.exists() and not args.output.is_symlink(),
            'Output already exists; preserve the earlier report')
    profile_path = Path(__file__).with_name('binding-layout.json')
    raw_profile = profile_path.read_bytes()
    profile = json.loads(raw_profile)
    report = {'pid': args.pid, 'mode': 'bindings' if args.read_bindings else 'mappings-only',
              'purpose': 'Read existing HMI runtime pointers; no loading, calls, writes or signals to HMI',
              'profile_sha256': hashlib.sha256(raw_profile).hexdigest(),
              'live_cds_callback_verified': False, 'live_rpm_verified': False}
    memory = None
    try:
        memory = memory_factory(args.target, args.pid)
        bases = parse_runtime_mappings(memory.header, memory.bases)
        report['mappings'] = {k: hex(v) for k, v in bases.items()}
        if args.read_bindings:
            report['observation'] = inspect_bindings(memory, bases, profile)
        report['result'] = 'completed'
    except (Refuse, OSError, ValueError, KeyError, TypeError, struct.error) as error:
        report['result'] = 'stopped'
        report['reason'] = str(error)
    finally:
        if memory:
            report['memory_bytes_read'] = memory.total
            report['memory_read_calls'] = memory.calls
            memory.close()
        with args.output.open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps(report, indent=2))
    print('Saved:', args.output)
    return 0 if report['result'] == 'completed' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Refuse, OSError, ValueError) as error:
        sys.exit(str(error))
