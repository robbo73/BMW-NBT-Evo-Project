#!/usr/bin/env python3
"""Offline fixtures only: execute the actual file scripts against temporary Linux paths."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import nbt_init_check as tool


class LocalConnection:
    """No network or QNX: stand in for SSH using a disposable local filesystem."""
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def run(self, script, data=None):
        return subprocess.run(['/bin/sh', '-c', script], input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'ID5'
        self.root.mkdir()
        self.plugins = self.root / 'Plugins'
        self.plugins.mkdir()
        self.hidden = self.root / tool.STAGE_NAME
        self.active = self.plugins / tool.TRIAL_NAME
        self.legacy = self.root / '.nbt-rpm-stage-09902c834a37'
        self.legacy.mkdir()
        (self.legacy / 'sentinel').write_bytes(b'older candidate untouched')
        self.data = {name: ('synthetic fixture: ' + name).encode() for name in tool.FILES}
        files = {name: (len(data), hashlib.sha256(data).hexdigest()) for name, data in self.data.items()}
        for name, value in [('ROOT', str(self.root)), ('PHYSICAL_ROOT', str(self.root)), ('FILES', files),
                            ('ARCHIVE_BYTES', tool.ARCHIVE_BYTES), ('ARCHIVE_SHA256', tool.ARCHIVE_SHA256)]:
            p = patch.object(tool, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.archive = self.root.parent / 'candidate.tar.gz'
        self.make_archive()
        self.connection = LocalConnection()
        self.record = {}
        self.save = lambda: None
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.errors = contextlib.redirect_stderr(io.StringIO())
        self.errors.__enter__()
        self.addCleanup(self.errors.__exit__, None, None, None)

    def make_archive(self, transform=None):
        with tarfile.open(self.archive, 'w:gz') as archive:
            for index, (name, data) in enumerate(self.data.items()):
                member = tarfile.TarInfo(tool.TRIAL_NAME + '/' + name)
                member.size = len(data)
                if transform:
                    transform(index, member)
                archive.addfile(member, io.BytesIO(data) if member.isfile() else None)
        tool.ARCHIVE_BYTES = self.archive.stat().st_size
        tool.ARCHIVE_SHA256 = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def stage(self, connection=None):
        tool.stage(connection or self.connection, tool.payloads(self.archive), self.record, self.save)

    def assert_legacy(self):
        self.assertEqual((self.legacy / 'sentinel').read_bytes(), b'older candidate untouched')

    def test_local_default_never_connects(self):
        with patch.object(tool, 'Connection', side_effect=AssertionError('unexpected SSH')):
            self.assertEqual(tool.main(['--archive', str(self.archive)]), 0)

    def test_wrong_hash_stops_before_ssh(self):
        self.archive.write_bytes(b'x' * tool.ARCHIVE_BYTES)
        with patch.object(tool, 'Connection', side_effect=AssertionError('unexpected SSH')):
            self.assertEqual(tool.main(['stage', '--archive', str(self.archive)]), 1)
        self.assertFalse(self.hidden.exists())

    def test_wrong_size_rejected(self):
        self.archive.write_bytes(b'bad')
        with self.assertRaisesRegex(RuntimeError, 'size differs'):
            tool.payloads(self.archive)

    def test_archive_link_rejected(self):
        def mutate(index, member):
            if index == 0:
                member.type = tarfile.SYMTYPE
                member.linkname = '/tmp/other'
        self.make_archive(mutate)
        with self.assertRaisesRegex(RuntimeError, 'type/size'):
            tool.payloads(self.archive)

    def test_archive_unexpected_path_rejected(self):
        self.make_archive(lambda i, member: setattr(member, 'name', '../escape') if i == 0 else None)
        with self.assertRaisesRegex(RuntimeError, 'members'):
            tool.payloads(self.archive)

    def test_archive_duplicate_rejected(self):
        first = next(iter(self.data))
        self.make_archive(lambda i, member: setattr(member, 'name', tool.TRIAL_NAME + '/' + first))
        with self.assertRaisesRegex(RuntimeError, 'members'):
            tool.payloads(self.archive)

    def test_payload_corruption_rejected(self):
        self.data[next(iter(self.data))] = b'wrong fixture'
        self.make_archive()
        with self.assertRaises(RuntimeError):
            tool.payloads(self.archive)

    def test_stage_sets_bytes_modes_and_stays_hidden(self):
        self.stage()
        self.assertFalse(self.active.exists())
        self.assertEqual(tool.status(self.connection), 'HIDDEN')
        for name, data in self.data.items():
            self.assertEqual((self.hidden / name).read_bytes(), data)
            self.assertEqual((self.hidden / name).stat().st_mode & 0o777,
                             0o755 if name.endswith('.so') else 0o644)
        self.assertEqual(self.hidden.stat().st_mode & 0o777, 0o755)
        self.assertEqual(len(self.record['verified_files']), 5)
        self.assert_legacy()

    def test_repeat_stage_refuses_existing_stage(self):
        self.stage()
        with self.assertRaisesRegex(RuntimeError, 'already exists'):
            self.stage()
        self.assert_legacy()

    def test_existing_active_refused(self):
        self.active.mkdir()
        with self.assertRaises(RuntimeError):
            self.stage()
        self.assertFalse(self.hidden.exists())

    def test_existing_old_active_refused(self):
        (self.plugins / 'NbtAad').mkdir()
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assertFalse(self.hidden.exists())

    def test_stage_symlink_refused(self):
        self.hidden.symlink_to(self.legacy, target_is_directory=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assert_legacy()

    def test_active_symlink_refused(self):
        self.active.symlink_to(self.legacy, target_is_directory=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assertFalse(self.hidden.exists())

    def test_plugins_symlink_refused(self):
        self.plugins.rmdir()
        self.plugins.symlink_to(self.legacy, target_is_directory=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assertFalse(self.hidden.exists())

    def test_missing_plugins_refused_without_creating_it(self):
        self.plugins.rmdir()
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assertFalse(self.hidden.exists())
        self.assertFalse(self.plugins.exists())

    def test_dangling_old_active_link_refused(self):
        (self.plugins / 'NbtAad').symlink_to(self.root / 'missing')
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage()
        self.assertFalse(self.hidden.exists())

    def test_physical_root_mismatch_refused(self):
        with patch.object(tool, 'PHYSICAL_ROOT', '/unexpected/root'):
            with self.assertRaises(subprocess.CalledProcessError):
                self.stage()
        self.assertFalse(self.hidden.exists())

    def test_interrupted_transfer_preserves_hidden_partial(self):
        base = self.connection
        class Interrupted(LocalConnection):
            def run(self, script, data=None):
                if data is not None:
                    raise subprocess.TimeoutExpired('mock SSH', 1)
                return base.run(script, data)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.stage(Interrupted())
        self.assertTrue(self.hidden.is_dir())
        self.assertFalse(self.active.exists())
        self.assert_legacy()

    def test_noclobber_preserves_unexpected_file(self):
        base = self.connection
        name = next(iter(self.data))
        class Racing(LocalConnection):
            def run(inner, script, data=None):
                if data is not None:
                    (self.hidden / name).write_bytes(b'preserve this')
                return base.run(script, data)
        with self.assertRaises(subprocess.CalledProcessError):
            self.stage(Racing())
        self.assertEqual((self.hidden / name).read_bytes(), b'preserve this')
        self.assertFalse(self.active.exists())

    def test_corrupt_readback_refused(self):
        base = self.connection
        class Corrupt(LocalConnection):
            def run(inner, script, data=None):
                result = base.run(script, data)
                return b'corrupted readback' if script.rstrip().endswith('cat "$nbt_stage/libNbtAadInitCheck.so"') else result
        with self.assertRaisesRegex(RuntimeError, 'Read-back mismatch'):
            self.stage(Corrupt())
        self.assertFalse(self.active.exists())

    def test_verify_does_not_modify_stage(self):
        self.stage()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.hidden.iterdir()}
        tool.verify_stage(self.connection, self.data, self.record, self.save)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.hidden.iterdir()}
        self.assertEqual(before, after)

    def test_verify_refuses_linked_payload(self):
        self.stage()
        name = next(iter(self.data))
        (self.hidden / name).unlink()
        (self.hidden / name).symlink_to(self.legacy / 'sentinel')
        with self.assertRaises(subprocess.CalledProcessError):
            tool.verify_stage(self.connection, self.data, self.record, self.save)

    def test_rollback_hides_only_trial_and_is_idempotent(self):
        self.stage()
        self.hidden.rename(self.active)  # Fixture setup only; production helper cannot promote.
        tool.rollback(self.connection, self.record, self.save)
        self.assertEqual(tool.status(self.connection), 'HIDDEN')
        self.assertTrue(self.record['rollback_move_completed'])
        tool.rollback(self.connection, self.record, self.save)
        self.assertFalse(self.record['rollback_move_completed'])
        self.assert_legacy()

    def test_rollback_refuses_conflict(self):
        self.hidden.mkdir()
        self.active.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'Both active and hidden'):
            tool.rollback(self.connection, self.record, self.save)
        self.assertTrue(self.hidden.exists() and self.active.exists())

    def test_rollback_absent_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'No trial directory'):
            tool.rollback(self.connection, self.record, self.save)

    def test_rollback_check_is_read_only(self):
        self.stage()
        report = self.root.parent / 'check.json'
        with patch.object(tool, 'Connection', return_value=self.connection):
            result = tool.main(['rollback-check', '--archive', str(self.archive), '--report', str(report)])
        self.assertEqual(result, 0)
        record = json.loads(report.read_text())
        self.assertFalse(record['rollback_move_exercised'])
        self.assertFalse(record['activation_requested'])
        self.assertEqual(tool.status(self.connection), 'HIDDEN')

    def test_existing_report_refused_before_connect(self):
        report = self.root.parent / 'report.json'
        report.write_text('preserve')
        with patch.object(tool, 'Connection', side_effect=AssertionError('unexpected SSH')):
            self.assertEqual(tool.main(['stage', '--archive', str(self.archive), '--report', str(report)]), 1)
        self.assertEqual(report.read_text(), 'preserve')

    def test_failed_transfer_report_records_phase(self):
        report = self.root.parent / 'stopped.json'
        base = self.connection
        class Interrupted(LocalConnection):
            def run(self, script, data=None):
                if data is not None:
                    raise subprocess.TimeoutExpired('mock SSH', 1)
                return base.run(script, data)
        with patch.object(tool, 'Connection', return_value=Interrupted()):
            self.assertEqual(tool.main(['stage', '--archive', str(self.archive), '--report', str(report)]), 1)
        record = json.loads(report.read_text())
        self.assertEqual(record['status'], 'stopped')
        self.assertEqual(record['phase'], 'write:libNbtAadInitCheck.so')
        self.assertTrue(self.hidden.is_dir())

    def test_no_activation_command(self):
        with self.assertRaises(SystemExit) as raised:
            tool.main(['activate'])
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
