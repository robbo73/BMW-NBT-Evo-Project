#!/usr/bin/env python3
"""Chromebook RAM-only dummy trial helper. Explicit subcommands; default is help."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SSH = ['ssh', '-T', '-oHostKeyAlgorithms=+ssh-rsa', '-oControlPath=none',
       '-oConnectTimeout=10', 'root@192.168.16.101']
BINS = (
    ('nbt_large_endpoint_586', '8f502b6394a0acd9c800358b9ed6605fdc2f8aa92f5dce32dde73653b1bc06f2', 15898,
     '/dev/shmem/nbt_large_endpoint_586_8f502b6394a0'),
    ('nbt_hold_reader_586', '9a54c7f4dba539d25861f6e98a018d778bec62eb86462b7b208138a4be34de79', 22345,
     '/dev/shmem/nbt_hold_reader_586_9a54c7f4dba5'),
    ('nbt_held_supervisor', '1b499e82eb1ef73b40b327fe7bd334206fc1d21713271c55d363defc11256a28', 27292,
     '/dev/shmem/nbt_held_supervisor_1b499e82eb1e'),
)
EXIT_LINE = re.compile(rb'NBT_HELD_LAUNCHER_EXIT status=(0|[1-9][0-9]{0,2})\n')


class Stop(Exception):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_local():
    manifest = ROOT / 'SHA256SUMS'
    if not manifest.is_file() or manifest.is_symlink():
        raise Stop('use the complete frozen nbt-held-expiry-ready folder')
    for line in manifest.read_text().splitlines():
        sha, name = line.split('  ', 1)
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise Stop('invalid local manifest path')
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != sha:
            raise Stop('local checksum/type mismatch: ' + name)
    for name, sha, size, _ in BINS:
        path = ROOT / 'bin' / name
        if path.is_symlink() or not path.is_file():
            raise Stop('missing or linked local executable: ' + name)
        raw = path.read_bytes()
        if len(raw) != size or digest(raw) != sha:
            raise Stop('frozen executable mismatch: ' + name)


def remote(script, data=b'', timeout=90):
    # Only fixed scripts/constants enter the remote command; no shell=True.
    command = 'on -f hu-omap /bin/sh -c ' + shlex.quote(script)
    return subprocess.run(SSH + [command], input=data, stdout=subprocess.PIPE,
                          timeout=timeout, check=False)


def readback(item):
    name, sha, size, target = item
    script = 'set -e\n[ -f '+target+' ]\n[ ! -L '+target+' ]\ncat '+target+'\n'
    result = remote(script)
    if result.returncode != 0 or len(result.stdout) != size or digest(result.stdout) != sha:
        raise Stop('RAM read-back failed: ' + name)
    print('VERIFIED: ' + name + ' ' + sha, flush=True)


def copy_ram():
    for item in BINS:
        name, _, _, target = item
        script = ('set -e\nif [ -L '+target+' ]; then echo STOP_LINK; exit 2; fi\n'
                  'if [ -e '+target+' ]; then echo NBT_RAM_EXISTS; exit 0; fi\n'
                  'umask 077\n(set -C; cat > '+target+')\nchmod 700 '+target+'\necho RAM_COPY_COMPLETE\n')
        result = remote(script, (ROOT/'bin'/name).read_bytes())
        if result.returncode != 0 or result.stdout not in (b'RAM_COPY_COMPLETE\n', b'NBT_RAM_EXISTS\n'):
            raise Stop('RAM transfer refused/failed: ' + name)
        # Existing content is never overwritten; reuse requires this exact read-back.
        readback(item)


def check_ram():
    for item in BINS:
        readback(item)


def help_only():
    check_ram()
    for name, _, _, target in BINS:
        result = remote('ulimit -c 0 || exit 1\n'+target+' --help\n'
                        'nbt_status=$?\necho NBT_HELD_HELP_EXIT status=$nbt_status\nexit $nbt_status\n')
        if result.returncode != 0 or not result.stdout.endswith(b'NBT_HELD_HELP_EXIT status=0\n'):
            raise Stop('help-only startup did not exit 0: ' + name)
        print(result.stdout.decode('ascii'), end='', flush=True)


def split_capture(raw):
    # Only the final exact shell-observed status trailer is removed. Preserve all
    # other bytes, including forbidden bytes which the assessor must reject.
    if len(raw) > 65536 + 100:
        raise Stop('capture exceeds the reviewed output bound')
    end = raw.rfind(b'\n', 0, len(raw)-1) + 1 if raw.endswith(b'\n') else -1
    if end < 0:
        raise Stop('missing complete launcher exit trailer')
    trailer = EXIT_LINE.fullmatch(raw[end:])
    if not trailer:
        raise Stop('missing complete launcher exit trailer')
    status = int(trailer.group(1))
    if status > 255:
        raise Stop('launcher exit status outside shell range')
    body = raw[:end]
    if re.search(rb'(?m)^NBT_HELD_LAUNCHER_EXIT ', body):
        raise Stop('repeated launcher exit trailer')
    return body, status


def load_gate():
    script = ROOT/'tools/held-expiry-supervisor/gate_trial.py'
    spec = importlib.util.spec_from_file_location('held_trial_gate', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(raw, transport_exit, gate):
    body, observed_exit = split_capture(raw)
    result = gate.decide(observed_exit, body, gate.load_assessor())
    result['ssh_exit'] = transport_exit
    result['transport_status_agrees'] = transport_exit == observed_exit
    if transport_exit != 0:
        result['reasons'].append('SSH/QNET command exited nonzero: '+str(transport_exit))
    if not result['transport_status_agrees']:
        result['reasons'].append('SSH/QNET status disagrees with shell-observed launcher status')
    if result['reasons']:
        result['decision'] = 'REJECT'
    return body, result


def trial():
    # Revalidate volatile RAM and help immediately before the only active trial.
    help_only()
    folder = Path(tempfile.mkdtemp(prefix='nbt-held-run-', dir=str(ROOT.parent)))
    print('Capture directory: '+str(folder), flush=True)
    metadata = {'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'purpose':'inert 586-byte held-descriptor expiry trial', 'decision':'REJECT',
                'live_rpm_verified':False, 'hmi_integration_verified':False}
    meta_path = folder/'result.json'
    meta_path.write_text(json.dumps(metadata,indent=2)+'\n')
    target = BINS[2][3]
    script = ('ulimit -c 0 || exit 1\n'+target+' --trial\n'
              'nbt_status=$?\necho NBT_HELD_LAUNCHER_EXIT status=$nbt_status\nexit $nbt_status\n')
    try:
        result = remote(script, timeout=90)
        (folder/'ssh.stdout.raw').write_bytes(result.stdout)
        body, assessment = evaluate(result.stdout, result.returncode, load_gate())
        (folder/'capture.hxc').write_bytes(body)
        metadata.update(assessment)
        metadata['raw_sha256'] = digest(result.stdout)
        metadata['capture_sha256'] = digest(body)
    except subprocess.TimeoutExpired as error:
        raw = error.output or b''
        (folder/'ssh.stdout.raw').write_bytes(raw)
        metadata['error'] = 'SSH/capture timeout; no successful trial result'
    except (Stop, OSError, ValueError) as error:
        metadata['error'] = str(error)
    finally:
        meta_path.write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2), flush=True)
    print('Saved: '+str(folder), flush=True)
    if metadata['decision'] != 'ACCEPT':
        raise Stop('held-descriptor trial not accepted; preserve and share the complete capture')
    print('ACCEPT: exact capture, launcher status 0, SSH status 0 and assessor PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',choices=['check-local','copy-ram','check-ram','help-only','trial'])
    args = parser.parse_args()
    if args.action is None:
        parser.print_help(); return 0
    try:
        check_local()
        if args.action == 'check-local': print('All local ready-package files and three executable pins verified.')
        elif args.action == 'copy-ram': copy_ram()
        elif args.action == 'check-ram': check_ram()
        elif args.action == 'help-only': help_only()
        else: trial()
    except (Stop, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('STOP: '+str(error),file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
