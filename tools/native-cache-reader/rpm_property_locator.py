#!/usr/bin/env python3
"""Read-only locator for an already-created engine.RPMSpeed CDS property.

Extends nbt_native_cache.py without modifying it. It never calls getProperty,
createProperty, bind or any other target function: it only walks the provider's
std::map red-black tree in a read snapshot and reads fields of the property
object if (and only if) a map node for the name already exists.

Layout facts (captured firmware; see static notes):
  CCarDataMainProvider (HMI libhmiremoting, ctor 0x19bdd0, getProperty 0x19a52c)
    +0x20  std::map<THmiString<char>, CCarDataProperty*> (find at 0x19d69c,
           comparator std::string::compare)
    +0x24  _M_header   color            (end() iterator)
    +0x28             parent == root
    +0x2c             leftmost
    +0x30             rightmost
    +0x34  node count
    node:  +0 color, +4 parent, +8 left, +0xc right, +0x10 key data pointer (COW),
           +0x14 value (property*)
  CCdsPropertyEngineRPMSpeed (108 bytes, createProperty 0x1efa40, base ctor 0x1a3a20)
    +0x00 vptr   +0x10 creator (TPC<...>*)   +0x14 byte enabled
    +0x1c handler-list sentinel {next,prev}  (bind 0x1a1c4c appends here; first handler
                                              on an empty list triggers _bind)
    +0x24 second list sentinel
    +0x60 environment   +0x64 CEngineSpeed2 proxy
    +0x68 byte subscribed   +0x69 byte bound   (both cleared by createProperty)
"""
import struct

from nbt_native_cache import CacheGraph, require, u32, pointer

NAME = b'engine.RPMSpeed'
MAX_DEPTH = 64          # red-black tree height for <= 4096 nodes is <= 24
MAX_NODES = 4096
MAX_LIST = 16

LAYOUT_DEFAULTS = {
    'property_vtable': 0x6ac7c0,   # libhmiremoting: vtable for CCdsPropertyEngineRPMSpeed + 8
    'creator_vtable': 0x6a4338,    # libhmiremoting: vtable for TPC<CCdsPropertyEngineRPMSpeed> + 8
}


class Snapshot:
    """Recheck each visited region; this is best-effort, not an atomic snapshot."""
    def __init__(self, graph):
        self.graph = graph
        self.regions = {}

    def read(self, address, size):
        data = self.graph.read(address, size)
        key = address, size
        if key in self.regions:
            require(data == self.regions[key], 'Observed memory changed during inspection')
        self.regions[key] = data
        return data

    def verify(self):
        for (address, size), original in self.regions.items():
            require(self.graph.read(address, size) == original,
                    'Observed memory changed during final recheck')


def _cow_string(graph, key_ptr):
    require(0x1000c <= key_ptr < 0xff000000, 'Invalid map key pointer')
    block = graph.read(key_ptr - 12, 12)
    length, capacity = u32(block), u32(block, 4)
    require(length <= 256 and length <= capacity, 'Unexpected map key length/capacity')
    data = graph.read(key_ptr, length + 1)
    require(data[-1:] == b'\0', 'Map key is not terminated')
    return data[:-1]


def _read_list(graph, sentinel):
    """Bounded walk of a std::list whose sentinel is embedded at `sentinel`."""
    nxt, prv = struct.unpack('<II', graph.read(sentinel, 8))
    handlers, node, previous, seen = [], nxt, sentinel, set()
    while node != sentinel:
        pointer(node)
        require(node not in seen and len(handlers) < MAX_LIST, 'Handler list cycle or bound exceeded')
        seen.add(node)
        n_next, n_prev, handler = struct.unpack('<III', graph.read(node, 12))
        require(n_prev == previous, 'Handler list back-link mismatch')
        handlers.append(pointer(handler))
        previous, node = node, n_next
    require(prv == previous, 'Handler list tail mismatch')
    return handlers


def lower_bound(graph, provider, name=NAME):
    """Replicates the target's std::map::find without invoking it.
    Returns (node_count, node_address or None, header_bytes)."""
    header = graph.read(provider + 0x24, 0x14)
    _color, root, left, right, count = struct.unpack('<5I', header)
    require(count <= MAX_NODES, 'Property map outside audited bounds')
    end = provider + 0x24
    if count == 0:
        require(root == 0 and left == end and right == end, 'Empty property map is malformed')
        return count, None, header
    require(root != 0, 'Property map root missing')
    require(left not in (0, end) and right not in (0, end), 'Invalid property map extrema')
    pointer(left)
    pointer(right)
    best, node, parent, seen = end, root, end, set()
    low, high = None, None
    while node:
        pointer(node)
        require(node not in seen, 'Property map cycle')
        seen.add(node)
        require(len(seen) <= min(MAX_DEPTH, count), 'Property map deeper than audited bound')
        _c, _p, lft, rgt, key_ptr, _v = struct.unpack('<6I', graph.read(node, 0x18))
        require(_c in (0, 1) and _p == parent, 'Invalid map node color/parent')
        key = _cow_string(graph, key_ptr)
        require((low is None or low < key) and (high is None or key < high),
                'Property map ordering is inconsistent')
        parent = node
        if key < name:          # std::string::compare is lexicographic by bytes, then length
            low = key
            node = rgt
        else:
            high = key
            best, node = node, lft
    if best == end:
        return count, None, header
    _c, _p, _l, _r, key_ptr, _v = struct.unpack('<6I', graph.read(best, 0x18))
    return count, (best if _cow_string(graph, key_ptr) == name else None), header


def inspect_rpm_property(graph, provider, expected_proxy=None, name=NAME):
    require(name == NAME, 'Only the reviewed RPM property is supported')
    snapshot = Snapshot(graph)
    checked = CacheGraph(snapshot, graph.bases, graph.layout)
    environment, vehicle, speed = checked.proxy(provider)
    if expected_proxy is not None:
        require(speed == expected_proxy, 'RPM proxy differs from expected cache-reader proxy')
    layout = dict(LAYOUT_DEFAULTS)
    layout.update({k: v for k, v in graph.layout.items() if k in LAYOUT_DEFAULTS})
    remoting = graph.bases['remoting']
    count, node, header = lower_bound(snapshot, provider, name)
    report = {'provider': hex(provider), 'map_node_count': count,
              'property_name': name.decode('ascii'), 'binding_history_verified': False,
              'snapshot_consistency': 'best_effort_rechecked_not_atomic'}
    if node is None:
        snapshot.verify()
        report.update(property_found=False, current_state='absent', interpretation=(
            'No matching map entry in this provider snapshot. This does not establish '
            'creation/binding history or the state of other providers.'))
        return report
    value = u32(snapshot.read(node + 0x14, 4))
    prop = pointer(value)
    checked.vtable(prop, remoting + layout['property_vtable'], 'engine-speed property')
    block = snapshot.read(prop, 0x6c)
    creator = u32(block, 0x10)
    checked.vtable(pointer(creator), remoting + layout['creator_vtable'], 'property creator')
    require(u32(block, 0x60) == environment and u32(block, 0x64) == speed,
            'Property environment/proxy differs from verified provider chain')
    require(block[0x14] in (0, 1) and block[0x68] in (0, 1) and block[0x69] in (0, 1),
            'Unexpected property boolean fields')
    handlers = _read_list(snapshot, prop + 0x1c)
    pending = _read_list(snapshot, prop + 0x24)
    snapshot.verify()
    enabled, subscribed, bound = block[0x14], block[0x68], block[0x69]
    proxy = u32(block, 0x64)
    report.update(
        property_found=True, property_address=hex(prop), creator_address=hex(creator),
        enabled_0x14=bool(enabled), subscribed_0x68=bool(subscribed), bound_0x69=bool(bound),
        handler_count=len(handlers), handler_addresses=[hex(h) for h in handlers],
        second_list_count=len(pending), environment_0x60=hex(u32(block, 0x60)),
        proxy_0x64=hex(proxy),
        proxy_matches_cache_reader=None if expected_proxy is None else proxy == expected_proxy)
    if not subscribed and not bound and not handlers:
        state = 'no_current_bind_observed'
        text = ('No handlers or current subscription/bind flags in this snapshot. '
                'Earlier binding followed by unbind cannot be excluded.')
    elif bound and handlers:
        state = 'bound_with_handlers'
        text = ('A handler is attached and the bind flag is set. This does not establish '
                'notification transmission, accepted status or fresh RPM.')
    else:
        state = 'mixed'
        text = 'Mixed state (flags and handler list disagree); report as found, do not infer.'
    report['interpretation'] = text
    report['current_state'] = state
    return report


def inspect_request_state(graph, proxy, expected_host=None):
    """Read-only snapshot of what the +0x34 request routine (HmiMain3D 0x20dc374)
    consults before it will send anything. The proxy address comes from the
    existing cache reader (already vtable-checked there).

      proxy+0x10  function-block host (CSvcBase*)       -> null: request reports error 4
      host+0x58   state; the request is only sent at 2  -> any other value: returns 1, sends nothing
      host+0x34   u16 device address, +0x36 FBlock id, +0x37 instance id
      proxy+0x18  u16 function id placed in the request
      proxy+0x60  valid byte   +0x64 timer handle   +0x68 timer period/argument
    """
    snapshot = Snapshot(graph)
    checked = CacheGraph(snapshot, graph.bases, graph.layout)
    checked.vtable(proxy, graph.layout['engine_speed_vtable'], 'engine-speed proxy')
    block = snapshot.read(proxy, 0x70)
    host = u32(block, 0x10)
    report = {'proxy': hex(proxy), 'function_id_0x18': u32(block, 0x18) & 0xffff,
              'valid_0x60': bool(block[0x60]), 'timer_handle_0x64': hex(u32(block, 0x64)),
              'timer_value_0x68': u32(block, 0x68), 'host_0x10': hex(host),
              'transmission_verified': False,
              'snapshot_consistency': 'best_effort_rechecked_not_atomic'}
    if host == 0:
        snapshot.verify()
        report['request_gate'] = 'host pointer is null: the request routine would report error 4'
        return report
    pointer(host)
    if expected_host is not None:
        require(host == expected_host, 'Request host differs from expected vehicle')
    checked.vtable(host, graph.layout['vehicle_vtable'], 'vehicle function block')
    hb = snapshot.read(host + 0x30, 0x2c)           # covers +0x30..+0x5b
    state = u32(hb, 0x58 - 0x30)
    require(state <= 64, 'Implausible function-block state: %d' % state)
    report.update(host_state_0x58=state, device_address_0x34=struct.unpack_from('<H', hb, 4)[0],
                  fblock_id_0x36=hb[6], instance_id_0x37=hb[7])
    report['request_gate'] = ('state is 2: this early state gate permits proceeding; transmission is unverified'
                              if state == 2 else
                              'state is %d, not 2: the request path would defer at this check if unchanged' % state)
    report['state_gate_eligible'] = state == 2
    snapshot.verify()
    return report
