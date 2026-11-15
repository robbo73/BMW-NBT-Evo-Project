#!/usr/bin/env python3
"""Stage the audited RPM candidate outside Plugins; never activate/restart HMI.

Run on the Chromebook: python3 stage_rpm_candidate.py [candidate.tar.gz]
Uses Python's standard library and the existing OpenSSH client only.
"""
import argparse
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile

HOST = 'root@192.168.16.101'
ROOT = '/var/opt/hmi/data/ID5'
PHYSICAL_ROOT = '/fs/sda1/opt/hmi/data/ID5'
STAGE = ROOT + '/.nbt-rpm-stage-09902c834a37'
ACTIVE = ROOT + '/Plugins/NbtAad'
ARCHIVE_SHA256 = '1518475e81354d59c2d03e3998196dadf4bd67008e55e97f32b5e7f460f8f69f'
FILES = {
    'libNbtAad.so': '09902c834a37f0fb92e075f5228d4442534df432d5f4c48c2d9c6f8137162679',
    'NbtAad.manifest': 'cc09123717fea5c41698c1ff4c08b4cd5dde620fda1b3d00b0e8699a3c621af2',
    'NbtAad.xml': '4a84717f83cee07e1f52cea95ddef932428e7c5470ee9227789dd045558d25e4',
    'NbtAad_ALL_Texts.zip': '2b3ad02ec34cc476f53539070e5da7d9da4143ce75452e94499ad536532ad14b',
    'NbtAad_ALL_Images.zip': '38539939b8cf14343176e765d82144447918e6f26298f813fa6597381537047c',
}


def payloads(path):
    archive = Path(path).read_bytes()
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError('Archive hash differs from the audited candidate; no SSH connection made.')
    result = {}
    # Parse the same bytes that were hashed; never extract untrusted paths.
    import io
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as t:
        members = t.getmembers()
        if len(members) != len(FILES) or {m.name for m in members} != set(FILES):
            raise RuntimeError('Unexpected or duplicate archive members.')
        for m in members:
            if not m.isfile() or m.size > 1024 * 1024:
                raise RuntimeError('Unexpected archive member type/size: ' + m.name)
            data = t.extractfile(m).read()
            if hashlib.sha256(data).hexdigest() != FILES[m.name]:
                raise RuntimeError('Payload hash mismatch: ' + m.name)
            result[m.name] = data
    return result


class Connection:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nbt-stage-ssh-')
        self.socket = str(Path(self.temp.name) / 'control')
        self.base = ['ssh', '-oHostKeyAlgorithms=+ssh-rsa',
                     '-oConnectTimeout=10', '-oControlPath=' + self.socket]
        try:
            subprocess.run(self.base + ['-oControlMaster=yes', '-oControlPersist=60',
                                       '-MNf', HOST], check=True)
        except BaseException:
            self.close()
            raise
        return self

    def run(self, script, data=None):
        command = 'on -f hu-omap /bin/sh -c ' + shlex.quote(script)
        return subprocess.run(self.base + ['-oControlMaster=no', HOST, command],
                              input=data, stdout=subprocess.PIPE,
                              check=True, timeout=90).stdout

    def close(self):
        try:
            subprocess.run(['ssh', '-S', self.socket, '-O', 'exit', HOST],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False, timeout=10)
        finally:
            self.temp.cleanup()

    def __exit__(self, *args):
        self.close()


def stage_files(connection, data):
    if set(data) != set(FILES):
        raise RuntimeError('Wrong payload set; stage not created.')
    for name, content in data.items():
        if hashlib.sha256(content).hexdigest() != FILES[name]:
            raise RuntimeError('Unverified payload; stage not created: ' + name)
    script = f'''set -eu
cd {ROOT}
[ "$(pwd -P)" = "{PHYSICAL_ROOT}" ]
if [ -e "{ACTIVE}" ] || [ -L "{ACTIVE}" ]; then
    echo "Existing NbtAad installation; refusing staging" >&2
    exit 1
fi
if [ -e "{STAGE}" ] || [ -L "{STAGE}" ]; then
    echo "Stage already exists; refusing to overwrite it" >&2
    exit 1
fi
umask 077
mkdir "{STAGE}"
echo NBTRPM_STAGE_CREATED
'''
    if connection.run(script) != b'NBTRPM_STAGE_CREATED\n':
        raise RuntimeError('Stage creation was not confirmed.')
    for name in FILES:
        path = STAGE + '/' + name
        # Noclobber also protects against a file unexpectedly appearing mid-run.
        script = f'set -eu\nset -C\ncat > "{path}"\necho NBTRPM_FILE_WRITTEN\n'
        if connection.run(script, data[name]) != b'NBTRPM_FILE_WRITTEN\n':
            raise RuntimeError('File write was not confirmed: ' + name)
        returned = connection.run('set -e\ncat "' + path + '"\n')
        if returned != data[name]:
            raise RuntimeError('Read-back mismatch: ' + name)
        print('VERIFIED:', name, FILES[name], flush=True)
    script = f'''set -eu
chmod 755 "{STAGE}/libNbtAad.so"
chmod 644 "{STAGE}/NbtAad.manifest" "{STAGE}/NbtAad.xml" "{STAGE}/NbtAad_ALL_Texts.zip" "{STAGE}/NbtAad_ALL_Images.zip"
chmod 755 "{STAGE}"
echo NBTRPM_STAGE_READY
'''
    if connection.run(script) != b'NBTRPM_STAGE_READY\n':
        raise RuntimeError('Stage permission setup was not confirmed.')
    print('STAGED ONLY:', STAGE)
    print('All five files read back correctly. Plugins was not created; HMI was not restarted.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', nargs='?', type=Path,
                        default=Path.home() / 'bmw-idrive/nbt-rpm-test-package.tar.gz')
    args = parser.parse_args()
    try:
        data = payloads(args.archive)
        print('Local archive and all five payload hashes verified.', flush=True)
        with Connection() as connection:
            stage_files(connection, data)
    except (OSError, RuntimeError, tarfile.TarError,
            subprocess.SubprocessError, KeyboardInterrupt) as exc:
        print('STOP:', str(exc), file=sys.stderr)
        print('No activation/restart was requested. A partial hidden stage may remain at ' + STAGE,
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
