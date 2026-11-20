#!/usr/bin/env python3
"""Client-side observer of existing, verified HMI cache objects. No target injection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shlex
import struct
import subprocess
import sys
import time


class Refuse(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Refuse(message)


def u32(data, offset=0):
    return struct.unpack_from('<I', data, offset)[0]


def pointer(value):
    require(isinstance(value, int) and 0x10000 <= value < 0xff000000
            and value % 4 == 0, 'Invalid or unaligned object pointer: %#x' % value)
    return value


def fnv1a(name):
    value = 0x811c9dc5
    for byte in name:
        value = ((value ^ byte) * 0x01000193) & 0xffffffff
    return value


def parse_header(lines, pid):
    require(any(re.match(r'^\s*%d\s' % pid, line)
                and '/opt/hmi/bin/zipped/HmiMain3D' in line for line in lines),
            'Requested PID is not the expected HmiMain3D process')
    bases = {}
    for line in lines:
        match = re.search(r'\b(libhmiplugin|libhmiremoting|libhmicoding|libstdc\+\+)\.so(?:\.6)?[!*\s]*@([0-9a-fA-F]+)\b', line)
        if match:
            key = {'libhmiplugin': 'plugin', 'libhmiremoting': 'remoting', 'libhmicoding': 'coding', 'libstdc++': 'cpp'}[match[1]]
            value = pointer(int(match[2], 16))
            require(key not in bases or bases[key] == value, 'Conflicting module mappings')
            bases[key] = value
    require({'plugin', 'remoting', 'cpp'}.issubset(bases), 'All required module mappings were not found')
    bases['hmi'] = 0  # HMI is the inspected fixed-address ET_EXEC, not a PIE.
    return bases


class SSHMemory:
    """One SSH session; native shell only invokes pidin and dd on /proc/PID/as."""
    def __init__(self, target, pid):
        require(re.fullmatch(r'[A-Za-z0-9_.@-]+', target) is not None, 'Invalid SSH target')
        require(1 <= pid <= 0x7fffffff, 'Invalid PID')
        server = '''set -eu
command -v dd >/dev/null
pidin -p %d ar
pidin -p %d mem
echo NBT_CACHE_READ_READY
while read nbt_skip nbt_words; do
    case "$nbt_skip:$nbt_words" in *[!0-9:]*|:*|*:) exit 2;; esac
    [ "$nbt_words" -ge 1 ] && [ "$nbt_words" -le 8192 ] || exit 2
    dd if=/proc/%d/as bs=4 skip="$nbt_skip" count="$nbt_words" 2>/dev/null || exit 1
done
''' % (pid, pid, pid)
        command = 'on -f hu-omap /bin/sh -c ' + shlex.quote(server)
        self.process = subprocess.Popen(
            ['ssh', '-T', '-oHostKeyAlgorithms=+ssh-rsa', '-oControlPath=none',
             '-oConnectTimeout=10', '-oServerAliveInterval=10',
             '-oServerAliveCountMax=2', target, command],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.total = 0
        self.calls = 0
        self.phase = 'mapping startup'
        self.header = []
        try:
            header_bytes = 0
            deadline = time.monotonic() + 120  # Allow interactive password entry.
            while True:
                line = bytearray()
                while not line.endswith(b'\n'):
                    line.extend(self._exact(1, deadline))
                    require(len(line) <= 2048, 'Unexpected SSH header line')
                text = line.decode('ascii', errors='strict').strip()
                if text == 'NBT_CACHE_READ_READY':
                    break
                self.header.append(text)
                header_bytes += len(line)
                require(len(self.header) <= 512 and header_bytes <= 131072,
                        'Unexpected SSH startup output')
            self.bases = parse_header(self.header, pid)
        except Refuse as error:
            self.close()
            raise Refuse('%s; SSH exit status: %s; last startup output: %s' %
                         (error, self.process.returncode,
                          ' | '.join(self.header[-4:]) or '(none)')) from error
        except BaseException:
            self.close()
            raise

    def _exact(self, count, deadline):
        output = bytearray()
        while len(output) < count:
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'Timed out reading SSH output')
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            require(bool(ready), 'Timed out reading SSH output')
            chunk = os.read(self.process.stdout.fileno(), count - len(output))
            require(bool(chunk), 'SSH closed during ' + getattr(self, 'phase', 'output read'))
            output.extend(chunk)
        return bytes(output)

    def read(self, address, size):
        require(0 < size <= 32768 and 0x10000 <= address
                and address + size < 0xff000000, 'Read outside bounded user memory')
        aligned = address & ~3
        length = ((address + size + 3) & ~3) - aligned
        require(length <= 32768, 'Aligned read exceeds transport bound')
        self.total += length
        self.calls += 1
        require(self.total <= 262144 and self.calls <= 512, 'Read budget exceeded')
        self.process.stdin.write(('%d %d\n' % (aligned // 4, length // 4)).encode('ascii'))
        self.process.stdin.flush()
        self.phase = 'process-memory read'
        data = self._exact(length, time.monotonic() + 10)
        return data[address - aligned:address - aligned + size]

    def close(self):
        process = getattr(self, 'process', None)
        if process is None:
            return
        if process.stdin and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()  # Local SSH reader only; no signal is sent to HMI.
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if process.stdout:
            process.stdout.close()


class CacheGraph:
    def __init__(self, memory, bases, layout):
        self.memory, self.bases, self.layout = memory, bases, layout

    def read(self, address, size):
        result = self.memory.read(address, size)
        require(len(result) == size, 'Incomplete memory read')
        return result

    def word(self, address):
        return u32(self.read(address, 4))

    def vtable(self, address, expected, label):
        require(self.word(pointer(address)) == expected, 'Unexpected ' + label + ' vtable')

    def verify_images(self):
        for key, check in self.layout['fingerprints'].items():
            block = self.read(self.bases[key] + check['offset'], check['bytes'])
            require(hashlib.sha256(block).hexdigest() == check['sha256'],
                    'Code/header fingerprint mismatch for ' + key)

    def find_cache(self, name=b'ICarDataServer'):
        require(isinstance(name, bytes) and 1 <= len(name) <= 128 and
                all(32 <= c < 127 for c in name), 'Invalid interface name')
        root = self.bases['plugin'] + self.layout['registry_offset']
        header = self.read(root, 20)
        buckets, count, entries = u32(header, 8), u32(header, 12), u32(header, 16)
        require(1 <= count <= 4096 and entries <= 4096, 'Registry is absent or outside audited bounds')
        pointer(buckets)
        index = fnv1a(name) % count
        node = self.word(buckets + index * 4)
        sentinel = self.word(buckets + count * 4)
        visited = set()
        found = None
        while node and node != sentinel:
            pointer(node)
            require(node not in visited and len(visited) < 64, 'Registry chain cycle or bound exceeded')
            visited.add(node)
            data = self.read(node, 12)
            key, value, following = struct.unpack('<III', data)
            # GNU COW string data need not be word-aligned, so validate it separately.
            require(0x1000c <= key < 0xff000000, 'Invalid registry key')
            length = self.word(key - 12)
            require(length <= 512, 'Unexpected registry key length')
            if length == len(name):
                if self.read(key, length + 1) == name + b'\0':
                    found = pointer(value)
                    break
            node = following
        require(self.read(root, 20) == header, 'Registry changed during lookup; stop and refresh')
        if found is None:
            raise Refuse(name.decode('ascii') + ' is not present in the existing cache; no entry was created')
        self.vtable(found, self.bases['plugin'] + self.layout['cache_vtable'], 'interface cache')
        return found

    def scope_providers(self, cache):
        snapshot = self.read(cache + 0x18, 12)
        buckets, count, entries = struct.unpack('<III', snapshot)
        require(1 <= count <= 4096 and entries <= 128, 'Scope table outside audited bounds')
        table = self.read(pointer(buckets), (count + 1) * 4)
        heads = struct.unpack('<' + 'I' * (count + 1), table)
        sentinel, seen, providers = heads[-1], set(), []
        for first in heads[:-1]:
            node, chain = first, set()
            while node and node != sentinel:
                pointer(node)
                require(node not in chain, 'Scope chain cycle')
                if node in seen:
                    break
                require(len(seen) < 128, 'Too many scope nodes')
                chain.add(node)
                seen.add(node)
                scope, tls, following = struct.unpack('<III', self.read(node, 12))
                pointer(scope)
                self.vtable(tls, self.bases['plugin'] + self.layout['tls_vtable'], 'scope cache')
                provider = self.word(tls + 8)
                if provider:
                    providers.append((scope, tls, pointer(provider)))
                node = following
        require(len(seen) == entries, 'Scope node count inconsistent with its table')
        require(self.read(cache + 0x18, 12) == snapshot, 'Scope table changed during read')
        require(bool(providers), 'No existing scope has a cached interface; nothing was initialized')
        return providers

    def proxy(self, provider):
        layout, bases = self.layout, self.bases
        self.vtable(provider, bases['remoting'] + layout['provider_vtable'], 'data server')
        environment = pointer(self.word(provider + layout['environment_offset']))
        self.vtable(environment, bases['remoting'] + layout['environment_vtable'], 'CDS environment')
        vehicle = pointer(self.word(environment + layout['vehicle_offset']))
        self.vtable(vehicle, layout['vehicle_vtable'], 'vehicle proxy')
        speed = vehicle + layout['engine_speed_offset']
        self.vtable(speed, layout['engine_speed_vtable'], 'engine-speed proxy')
        return environment, vehicle, speed

    def sample(self, tls, provider):
        require(self.word(tls + 8) == provider, 'Cached provider changed before sample')
        chain = self.proxy(provider)
        data = self.read(chain[2], 0x7c)
        require(u32(data) == self.layout['engine_speed_vtable'], 'Speed proxy changed during sample')
        raw = struct.unpack_from('<H', data, self.layout['raw_offset'])[0]
        valid = bool(data[self.layout['valid_offset']])
        registered = bool(u32(data, self.layout['registration_offset']))
        rpm = raw // 4 if registered and valid and raw != 65535 and raw // 4 <= 9000 else None
        require(self.proxy(provider) == chain and self.word(tls + 8) == provider,
                'Object chain changed during sample')
        return {'monotonic_time': time.monotonic(), 'raw_u16': raw,
                'status_valid': valid, 'registration_word_nonzero': registered,
                'cached_rpm': rpm, 'freshness': 'unverified',
                'proxy_address': hex(chain[2])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True, help='Fresh HmiMain3D PID on hu-omap')
    parser.add_argument('--target', default='root@192.168.16.101')
    parser.add_argument('--read-cache', action='store_true', help='Read the verified existing cache graph')
    parser.add_argument('--inspect-property', action='store_true',
                        help='Also inspect existing RPM property and request state (requires --read-cache)')
    parser.add_argument('--inspect-admission', action='store_true',
                        help='Observe coding predicates in existing variant servers (requires --read-cache)')
    parser.add_argument('--inspect-manager', action='store_true',
                        help='Read existing app-manager directory records (requires --read-cache)')
    parser.add_argument('--output', type=Path, default=Path('nbt-native-cache-report.json'))
    args = parser.parse_args()
    if args.inspect_property and not args.read_cache:
        parser.error('--inspect-property requires --read-cache')
    if args.inspect_admission and not args.read_cache:
        parser.error('--inspect-admission requires --read-cache')
    if args.inspect_manager and not args.read_cache:
        parser.error('--inspect-manager requires --read-cache')
    require(not args.output.exists() and not args.output.is_symlink(), 'Output already exists; preserve it first')
    layout = json.loads(Path(__file__).with_name('vehicle-layout.json').read_text())
    report = {'pid': args.pid, 'mode': 'cache' if args.read_cache else 'mappings-only',
              'purpose': 'Observe existing native cached data; no plugin or target probe is loaded',
              'live_cds_callback_verified': False, 'cluster_agreement_verified': False}
    memory = None
    try:
        memory = SSHMemory(args.target, args.pid)
        report['mappings'] = {k: hex(v) for k, v in memory.bases.items()}
        if args.read_cache:
            graph = CacheGraph(memory, memory.bases, layout)
            graph.verify_images()
            if args.inspect_manager:
                from plugin_manager import inspect_manager
                manager_layout = json.loads(Path(__file__).with_name('manager-layout.json').read_text())
                report['plugin_manager'] = inspect_manager(graph, manager_layout)
            if args.inspect_admission:
                from app_admission import inspect_admission
                admission_layout = json.loads(Path(__file__).with_name('admission-layout.json').read_text())
                report['app_admission'] = inspect_admission(graph, admission_layout)
            cache = graph.find_cache()
            providers = graph.scope_providers(cache)
            report['providers'] = []
            seen = set()
            for scope, tls, provider in providers:
                if provider in seen:
                    continue
                require(len(seen) < 4, 'More than four distinct providers; stop for review')
                seen.add(provider)
                provider_report = {'scope_address': hex(scope),
                                   'provider_address': hex(provider)}
                if args.inspect_property:
                    from rpm_property_locator import inspect_rpm_property, inspect_request_state
                    chain = graph.proxy(provider)
                    require(graph.word(tls + 8) == provider, 'Cached provider changed before property inspection')
                    provider_report['rpm_property'] = inspect_rpm_property(
                        graph, provider, expected_proxy=chain[2])
                    provider_report['request_state'] = inspect_request_state(
                        graph, chain[2], expected_host=chain[1])
                    require(graph.proxy(provider) == chain and graph.word(tls + 8) == provider,
                            'Provider chain changed during property inspection')
                samples = []
                for number in range(3):
                    if number:
                        time.sleep(0.5)
                    samples.append(graph.sample(tls, provider))
                provider_report['samples'] = samples
                report['providers'].append(provider_report)
        report['result'] = 'completed'
    except (Refuse, OSError, ValueError, BrokenPipeError) as error:
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
    # Optional inspectors must share this script's Refuse class and helpers.
    sys.modules['nbt_native_cache'] = sys.modules[__name__]
    try:
        sys.exit(main())
    except (Refuse, OSError, ValueError) as error:
        sys.exit(str(error))
