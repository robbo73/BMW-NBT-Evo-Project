"""Observe app-coding predicates without calling the native variant server."""
import hashlib
import struct

from nbt_native_cache import CacheGraph, require, pointer, u32
from rpm_property_locator import Snapshot


def _descriptor(snapshot, server, coding_base, layout):
    """Mirror the integer-key VA lookup and its checked bit comparison."""
    feature = layout['direct_feature']
    root = server + layout['va_map_offset']
    header = snapshot.read(root + 8, 12)
    buckets, count, entries = struct.unpack('<III', header)
    require(1 <= count <= 16384 and entries <= 4096, 'VA map outside audited bounds')
    pointer(buckets)
    node = u32(snapshot.read(buckets + (feature['id'] % count) * 4, 4))
    end = u32(snapshot.read(buckets + count * 4, 4))
    seen = set()
    descriptor = None
    while node and node != end:
        pointer(node)
        require(node not in seen and len(seen) < 64, 'VA map cycle or bound exceeded')
        seen.add(node)
        key, value, following = struct.unpack('<III', snapshot.read(node, 12))
        if key == feature['id']:
            descriptor = value
            break
        node = following
    result = {'feature': feature['name'], 'feature_id': feature['id'],
              'native_predicate_result': False, 'coding_data_available': False}
    if not descriptor:
        result['reason'] = 'Feature descriptor absent/null in this instance; native check returns false'
        return result
    require(pointer(descriptor) == coding_base + feature['descriptor_offset'],
            'Unexpected direct-feature descriptor')
    block = snapshot.read(descriptor, 36)
    require(u32(block, 0x14) == feature['id'] and
            u32(block, 0x18) == coding_base + feature['name_offset'] and
            struct.unpack_from('<H', block, 8)[0] == feature['page'] and
            struct.unpack_from('<H', block, 0xa)[0] == feature['byte_offset'] and
            struct.unpack_from('<H', block, 0xe)[0] == feature['extra_offset'] and
            block[0x10] == feature['mask'] and block[0x11] == feature['expected_value'],
            'Direct-feature descriptor differs from reviewed layout')
    data = u32(block, 0x1c)
    length = struct.unpack_from('<H', block, 0x20)[0]
    offset = feature['byte_offset'] + feature['extra_offset']
    if not data or offset >= length:
        result['reason'] = 'Coding buffer absent/too short; native check returns false'
        return result
    require(0x10000 <= data and data + offset < 0xff000000, 'Invalid coding-buffer pointer')
    raw = snapshot.read(data + offset, 1)[0]
    mask = feature['mask']
    require(1 <= mask <= 255, 'Invalid reviewed mask')
    shift = (mask & -mask).bit_length() - 1
    value = (raw & mask) >> shift
    result.update(coding_data_available=True, selected_value=value,
                  native_predicate_result=value == feature['expected_value'])
    return result


def _cached_iva(snapshot, server, feature, layout):
    address = server + layout['iva_array_offset'] + (feature - layout['iva_origin']) * layout['iva_stride']
    block = snapshot.read(address, 8)
    key = u32(block)
    require(key in (0, feature) and block[4] in (0, 1), 'Unexpected cached IVA entry')
    return {'feature_id': feature, 'entry_populated': key == feature,
            'native_predicate_result': bool(block[4]) if key == feature else False}


def inspect_admission(graph, layout):
    require('coding' in graph.bases, 'libhmicoding mapping not found; no base was guessed')
    for check in layout['fingerprints']:
        data = graph.read(graph.bases[check['module']] + check['offset'], check['bytes'])
        require(hashlib.sha256(data).hexdigest() == check['sha256'],
                'App-admission code fingerprint mismatch: ' + check['module'])
    snapshot = Snapshot(graph)
    checked = CacheGraph(snapshot, graph.bases, graph.layout)
    cache = checked.find_cache(b'IHmiVariantServer')
    interfaces = checked.scope_providers(cache)
    observed, seen = [], set()
    for scope, tls, server in interfaces:
        if server in seen:
            continue
        require(len(seen) < 8, 'Too many variant-server instances')
        seen.add(server)
        checked.vtable(server, graph.bases['coding'] + layout['variant_vtable'], 'variant server')
        require(checked.word(tls + 8) == server, 'Variant-server cache changed')
        role = checked.word(server + layout['role_offset'])
        direct = _descriptor(snapshot, server, graph.bases['coding'], layout)
        iva = {key: _cached_iva(snapshot, server, value, layout)
               for key, value in layout['iva_features'].items()}
        special = any(iva[key]['native_predicate_result'] for key in
                      ('special_security', 'special_authority_marked', 'special_authority_unmarked')) and role == 1
        derived = special or any(iva[key]['native_predicate_result']
                                for key in ('remote_hmi', 'apps', 'touch_command'))
        observed.append({'scope_address': hex(scope), 'variant_server_address': hex(server),
                         'role_value': role, 'direct_1a0': direct, 'cached_iva': iva,
                         'derived_9c55': special, 'derived_9c56': derived,
                         'predicate_for_this_instance': bool(direct['native_predicate_result'] or derived)})
    snapshot.verify()
    return {'instances': observed,
            'app_manager_scope_association_verified': False,
            'plugin_loading_verified': False,
            'interpretation': 'Observed coding predicate per cached variant server; does not prove which instance the app manager uses or any later loading stage.',
            'snapshot_consistency': 'best_effort_rechecked_not_atomic'}
