#!/usr/bin/env python3
"""Verify, stage or hide the frozen initialization check. No activation command."""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile


HOST = 'root@192.168.16.101'
ROOT = '/var/opt/hmi/data/ID5'
PHYSICAL_ROOT = '/fs/sda1/opt/hmi/data/ID5'
STAGE_NAME = '.nbt-init-check-stage-9cc395b60a97'
TRIAL_NAME = 'NbtAadInitCheck'
ARCHIVE_BYTES = 85888
ARCHIVE_SHA256 = 'a564109d08fdcbd71b232f8ac79fbe20f2e3dcd394017a7308c9c4f7099b8018'
FILES = {
    'libNbtAadInitCheck.so': (43757, '9cc395b60a97eea6b1d7ff9c1e58d98260bc90392bf1f6e466894e98b0d6329d'),
    'NbtAadInitCheck.manifest': (586, 'c74b96f7b9b36afbe71ef8b83b1eda5f162fdb388fb6ac6acb7c6a5243c9ae43'),
    'NbtAad.xml': (10951, '4a84717f83cee07e1f52cea95ddef932428e7c5470ee9227789dd045558d25e4'),
    'NbtAad_ALL_Texts.zip': (7487, '2b3ad02ec34cc476f53539070e5da7d9da4143ce75452e94499ad536532ad14b'),
    'NbtAad_ALL_Images.zip': (55671, '38539939b8cf14343176e765d82144447918e6f26298f813fa6597381537047c'),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def payloads(path):
    require(path.stat().st_size == ARCHIVE_BYTES, 'Candidate archive size differs; no SSH connection made')
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == ARCHIVE_SHA256,
            'Candidate archive hash differs; no SSH connection made')
    result = {}
    expected = {TRIAL_NAME + '/' + name for name in FILES}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = archive.getmembers()
        require(len(members) == len(FILES) and {m.name for m in members} == expected,
                'Unexpected or duplicate archive members')
        for member in members:
            name = member.name.split('/', 1)[1]
            size, digest = FILES[name]
            require(member.isfile() and member.size == size, 'Unexpected member type/size: ' + name)
            content = archive.extractfile(member).read()
            require(hashlib.sha256(content).hexdigest() == digest, 'Payload hash differs: ' + name)
            result[name] = content
    return result


class Connection:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nbt-init-check-ssh-')
        self.socket = str(Path(self.temp.name) / 'control')
        self.base = ['ssh', '-T', '-oHostKeyAlgorithms=+ssh-rsa', '-oConnectTimeout=10',
                     '-oServerAliveInterval=5', '-oServerAliveCountMax=2',
                     '-oControlPath=' + self.socket]
        try:
            subprocess.run(self.base + ['-oControlMaster=yes', '-oControlPersist=60',
                                       '-MNf', HOST], check=True, timeout=130)
        except BaseException:
            self.close()
            raise
        return self

    def run(self, script, data=None):
        command = 'on -f hu-omap /bin/sh -c ' + shlex.quote(script)
        return subprocess.run(self.base + ['-oControlMaster=no', HOST, command], input=data,
                              stdout=subprocess.PIPE, check=True, timeout=90).stdout

    def close(self):
        try:
            if Path(self.socket).exists():
                subprocess.run(['ssh', '-S', self.socket, '-O', 'exit', HOST], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        finally:
            self.temp.cleanup()

    def __exit__(self, *args):
        self.close()


def guard():
    return f'''set -eu
nbt_root={shlex.quote(ROOT)}
cd "$nbt_root"
[ "$(pwd -P)" = {shlex.quote(PHYSICAL_ROOT)} ]
nbt_plugins="$nbt_root/Plugins"
nbt_stage="$nbt_root/{STAGE_NAME}"
nbt_active="$nbt_plugins/{TRIAL_NAME}"
[ -d "$nbt_plugins" ]
[ ! -L "$nbt_plugins" ]
for nbt_cmd in cat mkdir chmod mv; do command -v "$nbt_cmd" >/dev/null; done
'''


def status(connection):
    script = guard() + '''
for nbt_path in "$nbt_stage" "$nbt_active"; do
    if [ -L "$nbt_path" ]; then echo "Refusing linked trial path" >&2; exit 1; fi
    if [ -e "$nbt_path" ] && [ ! -d "$nbt_path" ]; then echo "Refusing non-directory trial path" >&2; exit 1; fi
done
if [ -d "$nbt_stage" ] && [ -d "$nbt_active" ]; then echo CONFLICT
elif [ -d "$nbt_stage" ]; then echo HIDDEN
elif [ -d "$nbt_active" ]; then echo ACTIVE
else echo ABSENT
fi
'''
    result = connection.run(script).decode('ascii').strip()
    require(result in ('HIDDEN', 'ACTIVE', 'ABSENT', 'CONFLICT'), 'Unexpected preflight response')
    require(result != 'CONFLICT', 'Both active and hidden trial paths exist; nothing moved')
    return result


def hidden_guard():
    return guard() + '''
[ -d "$nbt_stage" ]
[ ! -L "$nbt_stage" ]
[ ! -e "$nbt_active" ]
[ ! -L "$nbt_active" ]
'''


def verify_stage(connection, data, record, save):
    require(status(connection) == 'HIDDEN', 'A single hidden stage is required')
    record['verified_files'] = []
    for name, (size, digest) in FILES.items():
        record['phase'] = 'read-back:' + name
        save()
        script = hidden_guard() + f'''[ -f "$nbt_stage/{name}" ]
[ ! -L "$nbt_stage/{name}" ]
cat "$nbt_stage/{name}"
'''
        returned = connection.run(script)
        require(returned == data[name], 'Read-back mismatch: ' + name)
        record['verified_files'].append({'name': name, 'bytes': size, 'sha256': digest})
        save()
        print('VERIFIED:', name, digest, flush=True)
    script = hidden_guard() + '''
[ -x "$nbt_stage" ]
[ -x "$nbt_stage/libNbtAadInitCheck.so" ]
echo NBT_INIT_CHECK_VERIFIED
'''
    require(connection.run(script) == b'NBT_INIT_CHECK_VERIFIED\n', 'Stage mode verification failed')


def stage(connection, data, record, save):
    require(status(connection) == 'ABSENT', 'Trial path already exists; use verify-stage for an existing hidden stage')
    script = guard() + '''
[ ! -e "$nbt_plugins/NbtAad" ]
[ ! -L "$nbt_plugins/NbtAad" ]
[ ! -e "$nbt_stage" ]
[ ! -L "$nbt_stage" ]
[ ! -e "$nbt_active" ]
[ ! -L "$nbt_active" ]
umask 077
mkdir "$nbt_stage"
echo NBT_INIT_CHECK_STAGE_CREATED
'''
    record['phase'] = 'create-hidden-stage'
    save()
    require(connection.run(script) == b'NBT_INIT_CHECK_STAGE_CREATED\n', 'Stage creation not confirmed')
    for name in FILES:
        record['phase'] = 'write:' + name
        save()
        script = hidden_guard() + f'''set -C
cat > "$nbt_stage/{name}"
echo NBT_INIT_CHECK_FILE_WRITTEN
'''
        require(connection.run(script, data[name]) == b'NBT_INIT_CHECK_FILE_WRITTEN\n',
                'File write not confirmed: ' + name)
    script = hidden_guard()
    for name in FILES:
        script += f'[ -f "$nbt_stage/{name}" ]\n[ ! -L "$nbt_stage/{name}" ]\n'
    script += 'chmod 755 "$nbt_stage/libNbtAadInitCheck.so"\n'
    script += 'chmod 644 ' + ' '.join('"$nbt_stage/' + n + '"' for n in FILES if not n.endswith('.so')) + '\n'
    script += 'chmod 755 "$nbt_stage"\necho NBT_INIT_CHECK_MODES_SET\n'
    record['phase'] = 'set-modes'
    save()
    require(connection.run(script) == b'NBT_INIT_CHECK_MODES_SET\n', 'Stage permissions not confirmed')
    verify_stage(connection, data, record, save)
    record['state'] = 'HIDDEN'
    print('STAGED ONLY:', ROOT + '/' + STAGE_NAME)


def rollback(connection, record, save):
    current = status(connection)
    require(current in ('HIDDEN', 'ACTIVE'), 'No trial directory found; nothing moved')
    record['phase'] = 'rollback'
    save()
    script = guard() + '''
[ ! -L "$nbt_stage" ]
[ ! -L "$nbt_active" ]
if [ -d "$nbt_stage" ] && [ ! -e "$nbt_active" ]; then
    echo NBT_INIT_CHECK_ALREADY_HIDDEN
else
    [ -d "$nbt_active" ]
    [ ! -e "$nbt_stage" ]
    mv "$nbt_active" "$nbt_stage"
    echo NBT_INIT_CHECK_HIDDEN
fi
'''
    result = connection.run(script)
    require(result in (b'NBT_INIT_CHECK_HIDDEN\n', b'NBT_INIT_CHECK_ALREADY_HIDDEN\n'),
            'Rollback move not confirmed; inspect paths')
    record['state'] = 'HIDDEN'
    record['rollback_move_completed'] = result == b'NBT_INIT_CHECK_HIDDEN\n'
    print('Trial is hidden. This does not unload an already running library.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='check-local',
                        choices=['check-local', 'preflight', 'stage', 'verify-stage', 'rollback-check', 'rollback'])
    parser.add_argument('--archive', type=Path,
                        default=Path(__file__).with_name('nbt-init-check-candidate.tar.gz'))
    parser.add_argument('--report', type=Path, help='New local JSON path; existing files are refused')
    args = parser.parse_args(argv)
    record = {'operation': args.command, 'host': HOST, 'activation_requested': False,
              'restart_requested': False, 'phase': 'local-verification'}
    try:
        data = payloads(args.archive.expanduser())
        print('Local archive and all five payload hashes verified.', flush=True)
        if args.command == 'check-local':
            return 0
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        report = (args.report.expanduser() if args.report else
                  Path.home() / 'bmw-idrive' / ('nbt-init-check-' + args.command + '-' + stamp + '.json'))
        require(not report.exists() and not report.is_symlink(), 'Report already exists; preserve it first')
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open('x') as output:
            def save():
                output.seek(0)
                json.dump(record, output, indent=2)
                output.write('\n')
                output.truncate()
                output.flush()
            record.update(status='started', candidate_sha256=ARCHIVE_SHA256,
                          hidden_stage=ROOT + '/' + STAGE_NAME,
                          active_path=ROOT + '/Plugins/' + TRIAL_NAME)
            save()
            try:
                record['phase'] = 'connect'
                save()
                with Connection() as connection:
                    if args.command == 'stage':
                        stage(connection, data, record, save)
                    elif args.command == 'verify-stage':
                        verify_stage(connection, data, record, save)
                        record['state'] = 'HIDDEN'
                    elif args.command == 'rollback':
                        rollback(connection, record, save)
                    else:
                        record['phase'] = 'read-only-preflight'
                        record['state'] = status(connection)
                        record['rollback_move_exercised'] = False
                        print('Current trial state:', record['state'])
                        if args.command == 'rollback-check':
                            require(record['state'] in ('HIDDEN', 'ACTIVE'), 'Stage the trial before checking rollback')
                            print('Path/utility checks passed. No move was performed.')
                record.update(status='completed', phase='done')
            except (OSError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt) as error:
                record['status'] = 'stopped'
                record['reason'] = ('SSH command failed with exit status ' + str(error.returncode)
                                    if isinstance(error, subprocess.CalledProcessError) else str(error))
            save()
        print('Saved:', report)
        if record['status'] != 'completed':
            raise RuntimeError(record['reason'])
        print('No activation or HMI restart was requested.')
        return 0
    except (OSError, RuntimeError, tarfile.TarError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        print('STOP:', error, file=sys.stderr)
        print('No activation/restart was requested. A partial hidden stage may remain; preserve it for inspection.',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
