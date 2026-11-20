"""Read existing app-manager directory records without invoking the loader."""
import hashlib
import struct

from nbt_native_cache import pointer, require, u32
from rpm_property_locator import Snapshot


def _path(snapshot, address):
    # BMW BasicString uses refcount/capacity/length, unlike GNU COW string.
    require(0x1000c <= address < 0xff000000, 'Invalid manager path pointer')
    header = snapshot.read(address - 12, 12)
    capacity, length = u32(header, 4), u32(header, 8)
    require(1 <= length <= 512 and length <= capacity <= 1048576,
            'Manager path length/capacity outside bounds')
    data = snapshot.read(address, length + 1)
    require(data[-1:] == b'\0' and data[:1] == b'/' and
            all(32 <= c < 127 for c in data[:-1]), 'Unexpected manager path string')
    return data[:-1].decode('ascii')


def inspect_manager(graph, layout):
    for check in layout['fingerprints']:
        block = graph.read(graph.bases['hmi'] + check['offset'], check['bytes'])
        require(hashlib.sha256(block).hexdigest() == check['sha256'],
                'Plugin-manager code fingerprint mismatch')
    snapshot = Snapshot(graph)
    global_address = graph.bases['hmi'] + layout['instance_pointer']
    manager = pointer(u32(snapshot.read(global_address, 4)))
    require(u32(snapshot.read(manager, 4)) == graph.bases['hmi'] + layout['manager_vtable'],
            'Unexpected app-manager vtable')
    header = snapshot.read(manager + 0x1c, 20)
    color, root, left, right, count = struct.unpack('<5I', header)
    require(color in (0, 1) and count <= 16, 'Manager directory count/color outside bounds')
    flag54 = snapshot.read(manager + 0x54, 1)[0]
    flag5c = snapshot.read(manager + 0x5c, 1)[0]
    require(flag54 in (0, 1) and flag5c in (0, 1),
            'Unexpected manager flag representation')
    end = manager + 0x1c
    if count == 0:
        require(root == 0 and left == end and right == end, 'Malformed empty manager tree')
    else:
        pointer(root)
        pointer(left)
        pointer(right)
    seen, records = set(), []

    def visit(node, parent, depth):
        if not node:
            return
        pointer(node)
        require(node != end and node not in seen and len(seen) < count and depth <= 16,
                'Manager directory tree cycle or bound exceeded')
        seen.add(node)
        data = snapshot.read(node, 24)
        node_color, actual_parent, child_left, child_right, key = struct.unpack_from('<5I', data)
        require(node_color in (0, 1) and actual_parent == parent,
                'Manager directory tree parent/color mismatch')
        require(data[0x14] in (0, 1), 'Unexpected coded-directory flag')
        visit(child_left, node, depth + 1)
        name = _path(snapshot, key)
        require(not records or records[-1]['path'] < name,
                'Manager directory paths are unordered or duplicated')
        records.append({'node_address': hex(node), 'path': name,
                        'coded_name_filter': bool(data[0x14])})
        visit(child_right, node, depth + 1)

    visit(root, end, 1)
    require(len(records) == count, 'Manager directory count inconsistent')
    if count:
        require(int(records[0]['node_address'], 16) == left and
                int(records[-1]['node_address'], 16) == right,
                'Manager directory extrema inconsistent')
    snapshot.verify()
    return {'manager_address': hex(manager), 'directory_count': count,
            'directories': records, 'raw_flag_0x54': flag54,
            'raw_flag_0x5c': flag5c,
            'snapshot_consistency': 'best_effort_rechecked_not_atomic',
            'plugin_loading_verified': False,
            'interpretation': 'Existing registered paths and coded-filter flags; does not prove a scan, admission or loading succeeded.'}
