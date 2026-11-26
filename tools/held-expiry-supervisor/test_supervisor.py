#!/usr/bin/env python3
"""Linux host end-to-end tests of the held-controller-1 launcher + supervisor (revision 2). SYNTHETIC only.

Nothing here runs on QNX or contacts the BMW, and passing does not establish QNX
compatibility. Each trial runs in a private mount namespace plus chroot in which
the fixed production paths exist (/ramdisk/mm, /dev/nbt_large_endpoint_586.*,
/dev/shmem pins), so the supervisor and the real reader are built from unchanged
source with no path substitution. The provider is always a stand-in (a regular
file, not a resource manager, with canned trace lines and a 3 s lease). The
reader is either the real nbt_hold_reader.c with the existing raw_faults.c
injectors, or a stand-in for misbehaviour the real reader cannot produce.
Every capture goes through the unchanged active assessor, loaded from the repo.

Requires root or unprivileged user+mount namespaces; otherwise the end-to-end
class is skipped (reported as skipped, never as passed). Namespace-free fault
regressions are in test_faults.py. The process started here is the launcher;
the supervisor (the contract's controller_pid, the reader's parent) is its child.
Location: tools/held-expiry-supervisor/ in the repository.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
READER_DIR = REPO / 'tools' / 'open-handle-expiry'
ASSESSOR_DIR = REPO / 'tools' / 'held-expiry-assessor'
PROVIDER_PIN = 'nbt_large_endpoint_586_8f502b6394a0'
READER_PIN = 'nbt_hold_reader_586_9a54c7f4dba5'
UNCHANGED = {   # SHA-256 at commit 0c9b390; the tests refuse to run against anything else
    ASSESSOR_DIR / 'assess_held_expiry.py': '84be7de262c5d3e982d187869440e5e18364a008ecfdf58f508405408b59b162',
    ASSESSOR_DIR / 'LOG-CONTRACT.md': 'cff0c7dffee0cc739a6b30a3060a816feecbd3d51fec4156152c40d5c8e4ee80',
    READER_DIR / 'nbt_hold_reader.c': '2e77faecf28f2a0a225606b6999b915b60910c0a506c86312ec01b612229ab7a',
    READER_DIR / 'large_body.c': 'b7973ea402990ef472a79b356e2c4ff71de97b55e77a51335250c41263d25b11',
    READER_DIR / 'large_body.h': '187b71d08191e65298918b57e28a4098644ad8be939078f57e365599630bd605',
    READER_DIR / 'test_support' / 'raw_faults.c': '89b9bd730ec7208e66a17c175312988c1e9d277f1492b56d802b8ec6d9a00fb1',
}
CFLAGS = ['-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror']
NS_SCRIPT = r'''set -eu
N=$1; T=$2; shift 2
mount --bind /usr "$N/usr"
mount --bind "$T/dev" "$N/dev"
mount --bind /dev/null "$N/dev/null"
mount --bind "$T/ramdisk_mm" "$N/ramdisk/mm"
mount --bind "$T/test" "$N/test"
exec chroot "$N" "$@"
'''


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_assessor():
    spec = importlib.util.spec_from_file_location('active_assessor', ASSESSOR_DIR / 'assess_held_expiry.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_gate():
    spec = importlib.util.spec_from_file_location('gate_trial', HERE / 'gate_trial.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def namespace_prefix():
    for prefix in (['unshare', '-m', '--propagation', 'private'] if os.geteuid() == 0 else [],
                   ['unshare', '-Urm', '--propagation', 'private']):
        if not prefix or not shutil.which('unshare'):
            continue
        probe = subprocess.run(prefix + ['sh', '-c', 'd=$(mktemp -d) && mount -t tmpfs t "$d" && umount "$d"'],
                               capture_output=True)
        if probe.returncode == 0:
            return prefix
    return None


def sections(raw):
    out = {}
    for match in re.finditer(rb'HXC1 seq=\d+ SECTION_BEGIN stream=([a-z.]+) bytes=(\d+)\n', raw):
        start = match.end()
        out[match.group(1).decode()] = raw[start:start + int(match.group(2))]
    return out


def records(raw, event):
    return [m.group(1).decode() for m in re.finditer(rb'^HXC1 seq=\d+ ' + event.encode() + rb'(?: ([^\n]*))?$', raw, re.M)]


def process_gone(pid):
    try:
        state = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0]
    except OSError:
        return True
    return state in ('Z', 'X')                 # an unreaped orphan zombie has exited


def command_line(pid):
    try:
        return Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')[0].decode(errors='replace')
    except OSError:
        return ''


def marked_processes(marker):
    needle = ('NBT_TRIAL_ID=%s\0' % marker).encode()
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if needle in (entry / 'environ').read_bytes():
                found.append(int(entry.name))
        except OSError:
            continue
    return found


class Build:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nbt-sup-host-')
        self.dir = Path(self.temp.name)
        src = HERE / 'nbt_held_supervisor.c'
        self.supervisor = self.dir / 'supervisor'
        self.supervisor_test = self.dir / 'supervisor_uninterruptible_output'
        self.reader = self.dir / 'reader'
        self.provider = self.dir / 'stub_provider'
        self.stub_reader = self.dir / 'stub_reader'
        # Production source, no path or timing definitions.
        self.run(['cc', *CFLAGS, str(src), '-o', str(self.supervisor), '-lrt'])
        # The single host-test switch, in a separately named binary.
        self.run(['cc', *CFLAGS, '-DNBT_TEST_UNINTERRUPTIBLE_OUTPUT', str(src), '-o', str(self.supervisor_test), '-lrt'])
        # Real reader: unchanged source and paths, plus the existing host fault injectors.
        self.run(['cc', *CFLAGS, '-I', str(READER_DIR), str(READER_DIR / 'nbt_hold_reader.c'),
                  str(READER_DIR / 'large_body.c'), str(READER_DIR / 'test_support' / 'raw_faults.c'),
                  *['-Wl,--wrap=' + n for n in ('read', '__read_chk', 'write', 'lseek', 'close', 'sigwaitinfo')],
                  '-o', str(self.reader)])
        self.run(['cc', *CFLAGS, '-I', str(READER_DIR), str(HERE / 'test_support' / 'stub_provider.c'),
                  str(READER_DIR / 'large_body.c'), '-o', str(self.provider)])
        self.run(['cc', *CFLAGS, str(HERE / 'test_support' / 'stub_reader.c'), '-o', str(self.stub_reader)])
        (self.dir / 'ns.sh').write_text(NS_SCRIPT)

    @staticmethod
    def run(command):
        subprocess.run(command, check=True)


class Trial:
    """One supervisor run in its own namespace/chroot with host-visible dev/ramdisk dirs."""

    def __init__(self, build, prefix, provider='normal', fault='', stub_reader=None,
                 action=None, target='launcher', blocked_stdout=False, uninterruptible=False):
        self.build, self.prefix = build, prefix
        self.provider_mode, self.fault, self.stub_mode = provider, fault, stub_reader
        self.action, self.target = action, target
        self.blocked, self.uninterruptible = blocked_stdout, uninterruptible
        self.marker = uuid.uuid4().hex
        self.root = Path(tempfile.mkdtemp(prefix='nbt-trial-', dir=build.dir))
        new = self.root / 'newroot'
        for name in ('usr', 'dev', 'test', 'ramdisk/mm'):
            (new / name).mkdir(parents=True)
        for name in ('bin', 'lib', 'lib64', 'sbin'):
            if Path('/' + name).is_symlink():
                (new / name).symlink_to(os.readlink('/' + name))
        (self.root / 'dev' / 'shmem').mkdir(parents=True)
        (self.root / 'dev' / 'null').touch()
        (self.root / 'ramdisk_mm').mkdir()
        (self.root / 'test').mkdir()
        shutil.copy2(build.provider, self.root / 'dev' / 'shmem' / PROVIDER_PIN)
        shutil.copy2(build.stub_reader if stub_reader else build.reader, self.root / 'dev' / 'shmem' / READER_PIN)
        shutil.copy2(build.supervisor_test if uninterruptible else build.supervisor, self.root / 'test' / 'supervisor')

    def command(self, *args):
        return [*self.prefix, 'sh', str(self.build.dir / 'ns.sh'), str(self.root / 'newroot'), str(self.root),
                '/test/supervisor', *args]

    def env(self):
        env = dict(os.environ, NBT_TRIAL_ID=self.marker, NBT_STUB_PROVIDER=self.provider_mode, NBT_RAW_FAULT=self.fault)
        if self.stub_mode:
            env['NBT_STUB_READER'] = self.stub_mode
        return env

    def held_visible(self, timeout=10):
        """Wait for the HELD line; return the supervisor PID taken from the fixture name."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for out in (self.root / 'ramdisk_mm').glob('.nbt-held-alias-586.*/reader.out'):
                try:
                    if b'\nHELD ' in out.read_bytes():
                        return int(out.parent.name.rsplit('.', 1)[1])
                except (OSError, ValueError):
                    pass
            time.sleep(0.02)
        return None

    def run(self):
        result = {'trial': self}
        started = time.monotonic()
        if self.blocked:
            read_end, write_end = os.pipe()
            os.set_blocking(write_end, False)
            filler = 0
            try:
                while True:
                    filler += os.write(write_end, b'.' * 4096)
            except BlockingIOError:
                pass
            os.set_blocking(write_end, True)       # the supervisor must meet a blocking, full pipe
            proc = subprocess.Popen(self.command('--trial'), env=self.env(), stdout=write_end, stderr=subprocess.PIPE)
            os.close(write_end)
            _, err = proc.communicate(timeout=60)
            result['elapsed'] = time.monotonic() - started
            os.set_blocking(read_end, False)
            drained = b''
            try:
                while True:
                    chunk = os.read(read_end, 65536)
                    if not chunk:
                        break
                    drained += chunk
            except BlockingIOError:
                pass
            os.close(read_end)
            result['out'] = drained[filler:]
        else:
            proc = subprocess.Popen(self.command('--trial'), env=self.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if self.action:
                supervisor_pid = self.held_visible()
                result['held_seen'] = supervisor_pid is not None
                result['supervisor_pid'] = supervisor_pid
                result['before'] = {pid: command_line(pid) for pid in marked_processes(self.marker)
                                    if pid not in (proc.pid, supervisor_pid)}
                if self.target == 'supervisor' and supervisor_pid:
                    os.kill(supervisor_pid, self.action)   # a child of the launcher, not of this test
                else:
                    proc.send_signal(self.action)
                result['signalled_at'] = time.monotonic() - started
            out, err = proc.communicate(timeout=60)
            result['elapsed'] = time.monotonic() - started
            result['out'] = out
        result['rc'] = proc.returncode
        result['err'] = err
        result['launcher_pid'] = proc.pid
        if self.action == signal.SIGKILL and self.target == 'supervisor':
            result['after_kill'] = self.watch_survivors(result['before'], limit=30)
        time.sleep(0.3)
        result['survivors'] = marked_processes(self.marker)
        result['fixtures'] = sorted(p.name for p in (self.root / 'ramdisk_mm').iterdir())
        result['endpoints'] = sorted(p.name for p in (self.root / 'dev').iterdir() if p.name.startswith('nbt_large_endpoint_586.'))
        return result

    @staticmethod
    def watch_survivors(before, limit):
        """After the supervisor was SIGKILLed: seconds until each of its other processes exits."""
        start = time.monotonic()
        gone = {command: None for command in before.values()}
        while time.monotonic() - start < limit and None in gone.values():
            for pid, command in before.items():
                if gone[command] is None and process_gone(pid):
                    gone[command] = time.monotonic() - start
            time.sleep(0.05)
        return gone


SCENARIOS = {
    'pass': {},
    'requested101': {'provider': 'requested101'},
    'nul_before_ready': {'provider': 'nul_before_ready'},
    'nul_in_trace': {'provider': 'nul_in_trace'},
    'provider_stderr': {'provider': 'stderr'},
    'provider_exit1': {'provider': 'exit1'},
    'provider_early_exit': {'provider': 'early_exit'},
    'provider_never_ready': {'provider': 'never_ready'},
    'provider_hang': {'provider': 'hang', 'stub_reader': 'ignore_release'},
    'provider_hang_real_reader': {'provider': 'hang'},
    'no_detached': {'provider': 'no_detached'},
    'endpoint_kept': {'provider': 'keep_endpoint'},
    'cleanup_interrupted': {'provider': 'litter'},
    'reader_control_fails': {'fault': 'control_read'},
    'reader_dies_during_hold': {'stub_reader': 'die_after_held'},
    'reader_extra_output': {'stub_reader': 'extra_before_release'},
    'reader_nul_after_release': {'stub_reader': 'nul_after_release'},
    'probe_zero_read': {'fault': 'zero'},
    'probe_stalls': {'fault': 'read_hang'},
    'reader_ignores_release': {'stub_reader': 'ignore_release'},
    'external_term': {'action': signal.SIGTERM},                       # sent to the launcher
    'supervisor_killed': {'action': signal.SIGKILL, 'target': 'supervisor'},
    'launcher_killed': {'action': signal.SIGKILL},
    'blocked_stdout': {'blocked_stdout': True},
    'launcher_hard_stop': {'blocked_stdout': True, 'uninterruptible': True},
}
NS = namespace_prefix()


class UnchangedInputs(unittest.TestCase):
    def test_active_assessor_contract_reader_and_endpoint_inputs_are_unchanged(self):
        for path, digest in UNCHANGED.items():
            self.assertEqual(sha256(path), digest, str(path))


class SupervisorSource(unittest.TestCase):
    SOURCE = (HERE / 'nbt_held_supervisor.c').read_text()

    def test_production_paths_are_fixed_in_source(self):
        for line in ('#define NBT_ROOT "/ramdisk/mm"', '#define NBT_ENDPOINT_PREFIX "/dev/nbt_large_endpoint_586."',
                     '#define NBT_PROVIDER_BIN "/dev/shmem/' + PROVIDER_PIN + '"',
                     '#define NBT_READER_BIN "/dev/shmem/' + READER_PIN + '"'):
            self.assertIn(line, self.SOURCE)
        self.assertNotIn('#ifndef NBT_ROOT', self.SOURCE)
        self.assertNotIn('getenv', self.SOURCE)

    def test_signals_only_through_the_ownership_check(self):
        calls = re.findall(r'\bkill\(([^,]+),', self.SOURCE)
        self.assertEqual(calls, ['c->pid'])
        self.assertNotIn('getppid', self.SOURCE)
        self.assertNotRegex(self.SOURCE, r'\bwait\(')
        self.assertEqual(re.findall(r'waitpid\(([^,]+),', self.SOURCE), ['c->pid'])
        self.assertIn('if (!c->owned) { errno = ESRCH; return -1; }', self.SOURCE)

    def test_host_test_switches_cannot_compile_for_qnx(self):
        for switch in ('-DNBT_TEST_UNINTERRUPTIBLE_OUTPUT', '-DNBT_UNIT_TEST'):
            result = subprocess.run(['cc', '-std=gnu99', '-fsyntax-only', '-D__QNX__', switch,
                                     str(HERE / 'nbt_held_supervisor.c')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, switch)
            self.assertIn('host-test builds only', result.stderr)

    def test_help_bad_arguments_and_missing_root_do_nothing(self):
        build = Build()
        try:
            for args, rc in (([], 0), (['--help'], 0), (['--trial', 'x'], 2), (['activate'], 2)):
                result = subprocess.run([str(build.supervisor), *args], capture_output=True, cwd=build.temp.name)
                self.assertEqual(result.returncode, rc, args)
                self.assertNotIn(b'HXC1', result.stdout)
            if not Path('/ramdisk/mm').exists():
                result = subprocess.run([str(build.supervisor), '--trial'], capture_output=True)
                self.assertEqual((result.returncode, result.stdout), (2, b''))
                self.assertIn(b'STOP: RAM root unavailable', result.stderr)
        finally:
            build.temp.cleanup()


@unittest.skipUnless(NS, 'needs root or user+mount namespaces for the production-path chroot')
class SupervisorEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.A = load_assessor()
        cls.gate = load_gate()
        cls.build = Build()
        trials = {name: Trial(cls.build, NS, **kwargs) for name, kwargs in SCENARIOS.items()}
        with ThreadPoolExecutor(max_workers=len(trials)) as pool:
            futures = {name: pool.submit(trial.run) for name, trial in trials.items()}
        cls.r = {}
        for name, future in futures.items():
            result = future.result()
            result['report'] = cls.A.assess(result['out'])          # every capture, unchanged assessor
            result['gate'] = cls.gate.decide(result['rc'], result['out'], cls.A)['decision']
            cls.r[name] = result

    @classmethod
    def tearDownClass(cls):
        cls.build.temp.cleanup()

    def assert_no_release(self, r):
        self.assertEqual(records(r['out'], 'RELEASE_SENT'), [])
        self.assertNotIn(b'RELEASED sender=', sections(r['out']).get('reader.stdout', b''))

    def assert_aborted(self, r, reason):
        self.assertEqual(records(r['out'], 'ABORT'), ['reason=' + reason])
        self.assertEqual(records(r['out'], 'END'), ['result=aborted'])
        self.assertEqual(r['rc'], 1, r['err'])
        self.assertNotEqual(r['report']['verdict'], 'PASS')

    def assert_tidy(self, r):
        self.assertEqual(r['survivors'], [])
        self.assertEqual(r['fixtures'], [])
        self.assertEqual(len(records(r['out'], 'FIXTURE_CLEANED')), 1)

    def test_every_capture_assessed_and_only_the_normal_trial_is_accepted(self):
        for name, r in self.r.items():
            with self.subTest(name):
                self.assertIn('verdict', r['report'])
                self.assertEqual(r['gate'] == 'ACCEPT', name == 'pass', (r['rc'], r['report']['findings']))
                if r['report']['verdict'] == 'PASS':
                    self.assertIn(name, ('pass', 'launcher_killed'))

    def test_normal_trial(self):
        r = self.r['pass']
        self.assertEqual(r['rc'], 0, r['err'])
        self.assertEqual(r['report']['verdict'], 'PASS', r['report']['findings'])
        self.assertEqual(r['gate'], 'ACCEPT')
        self.assertEqual(r['err'], b'')
        self.assert_tidy(r)
        self.assertNotEqual(int(records(r['out'], 'BEGIN')[0].split('controller_pid=')[1].split()[0]), r['launcher_pid'])
        self.assertEqual(r['endpoints'], [])
        events = [m.group(1).decode() for m in re.finditer(rb'^HXC1 seq=\d+ ([A-Z_]+)', r['out'], re.M)]
        self.assertLess(events.index('CONTROL_TRACE_OK'), events.index('RELEASE_SENT'))
        self.assertLess(events.index('FIXTURE_CLEANED'), events.index('WATCHDOG_CANCELLED'))

    def test_requested_101_blocks_release(self):
        r = self.r['requested101']
        self.assert_aborted(r, 'control_trace_invalid')
        self.assert_no_release(r)
        self.assertEqual(records(r['out'], 'CONTROL_TRACE_OK'), [])
        self.assertIn(b'requested=101', sections(r['out'])['provider.stdout'])
        self.assertEqual(records(r['out'], 'READER_REAPED')[0].split()[-1], 'status=137')
        self.assert_tidy(r)

    def test_injected_nuls_are_preserved_exactly_and_never_pass(self):
        r = self.r['nul_before_ready']
        self.assert_aborted(r, 'provider_output_unexpected')
        self.assertEqual(records(r['out'], 'READER_STARTED'), [])
        pid = records(r['out'], 'PROVIDER_STARTED')[0].split('=')[1]
        self.assertEqual(sections(r['out'])['provider.stdout'],
                         b'\0READY pid=%s path=/dev/nbt_large_endpoint_586.%s bytes=586 lease_ms=10000\n'
                         % (pid.encode(), pid.encode()))
        self.assertEqual(r['report']['verdict'], 'MALFORMED')
        r = self.r['nul_in_trace']
        self.assert_aborted(r, 'control_trace_invalid')
        self.assert_no_release(r)
        self.assertIn(b'dropped=0\0overflow=0', sections(r['out'])['provider.stdout'])
        r = self.r['reader_nul_after_release']
        self.assert_aborted(r, 'capture_invalid')
        self.assertEqual(len(records(r['out'], 'RELEASE_SENT')), 1)
        self.assertIn(b'OP_END name=read64_a rc=-1 errno=9\0 elapsed_ms=0\n', sections(r['out'])['reader.stdout'])
        self.assertEqual(r['report']['verdict'], 'MALFORMED')

    def test_provider_stderr_blocks_release(self):
        r = self.r['provider_stderr']
        self.assert_aborted(r, 'control_trace_invalid')
        self.assert_no_release(r)
        self.assertEqual(sections(r['out'])['provider.stderr'], b'synthetic provider diagnostic\n')

    def test_abnormal_provider_exits_block_release(self):
        for name, reason in (('provider_exit1', 'provider_abnormal_exit'), ('no_detached', 'control_trace_invalid'),
                             ('endpoint_kept', 'endpoint_present'), ('provider_never_ready', 'provider_not_ready')):
            with self.subTest(name):
                r = self.r[name]
                self.assert_aborted(r, reason)
                self.assert_no_release(r)
                self.assertEqual(r['survivors'], [])
        self.assertEqual(records(self.r['provider_exit1']['out'], 'PROVIDER_REAPED')[0].split()[-1], 'status=1')
        self.assertEqual(records(self.r['provider_never_ready']['out'], 'PROVIDER_REAPED')[0].split()[-1], 'status=137')
        r = self.r['provider_early_exit']
        self.assertIn(records(r['out'], 'ABORT')[0], ('reason=provider_exited_early', 'reason=reader_exited_early'))
        self.assert_no_release(r)

    def test_premature_reader_death_blocks_release(self):
        for name, reason, status in (('reader_dies_during_hold', 'reader_exited_early', 'status=3'),
                                     ('reader_control_fails', 'reader_exited_early', 'status=1'),
                                     ('reader_extra_output', 'reader_output_unexpected', 'status=137')):
            with self.subTest(name):
                r = self.r[name]
                self.assert_aborted(r, reason)
                self.assert_no_release(r)
                self.assertEqual(records(r['out'], 'READER_REAPED')[0].split()[-1], status)
                self.assert_tidy(r)

    def test_stalled_probes_are_bounded(self):
        r = self.r['probe_stalls']           # real reader: its own 3 s probe alarm
        self.assertEqual(records(r['out'], 'READER_REAPED')[0].split()[-1], 'status=142')
        self.assertEqual(records(r['out'], 'END'), ['result=complete'])
        self.assertEqual(r['report']['verdict'], 'TIMEOUT_OR_TERMINATED')
        r = self.r['reader_ignores_release']  # stand-in blocks every signal: supervisor deadline
        self.assertEqual(records(r['out'], 'WATCHDOG_FIRED'), ['target=reader'])
        self.assertEqual(records(r['out'], 'READER_REAPED')[0].split()[-1], 'status=137')
        self.assertGreaterEqual(r['elapsed'], 25)
        self.assertLess(r['elapsed'], 28)
        self.assert_tidy(r)
        r = self.r['probe_zero_read']
        self.assertEqual(r['report']['verdict'], 'UNEXPECTED_PROBE_RESULT')

    def test_reader_hold_alarm_ends_a_hold_on_a_provider_that_never_exits(self):
        r = self.r['provider_hang_real_reader']     # the real reader's own 18 s hold alarm comes first
        self.assert_aborted(r, 'reader_exited_early')
        self.assert_no_release(r)
        self.assertEqual(records(r['out'], 'READER_REAPED')[0].split()[-1], 'status=142')
        self.assertEqual(records(r['out'], 'PROVIDER_REAPED')[0].split()[-1], 'status=137')
        self.assert_tidy(r)

    def test_watchdog_bounds_a_provider_that_never_exits(self):
        r = self.r['provider_hang']                 # stand-in reader blocks every signal
        self.assertEqual(records(r['out'], 'WATCHDOG_FIRED'), ['target=both'])
        self.assert_no_release(r)
        self.assertGreaterEqual(r['elapsed'], 25)
        self.assertLess(r['elapsed'], 28)
        self.assert_tidy(r)

    def test_interrupted_cleanup_preserves_remaining_fixture(self):
        r = self.r['cleanup_interrupted']
        self.assert_aborted(r, 'cleanup_failed')
        self.assertEqual(records(r['out'], 'FIXTURE_CLEANED'), [])
        self.assertEqual(len(r['fixtures']), 1)
        left = sorted(p.name for p in (r['trial'].root / 'ramdisk_mm' / r['fixtures'][0]).iterdir())
        self.assertEqual(left, ['litter'])         # only the unexpected entry; owned files removed
        self.assertEqual(r['survivors'], [])

    def test_external_signal_takes_the_abort_path(self):
        r = self.r['external_term']
        self.assertTrue(r['held_seen'])
        self.assert_aborted(r, 'external_signal')
        self.assert_no_release(r)
        self.assert_tidy(r)

    def test_blocked_stdout_is_bounded_by_the_output_deadline(self):
        r = self.r['blocked_stdout']
        self.assertEqual(r['rc'], 3)               # supervisor exited by itself; launcher propagated 3
        self.assertGreaterEqual(r['elapsed'], 28)
        self.assertLess(r['elapsed'], 30)
        self.assertEqual(r['survivors'], [])
        self.assertEqual(r['fixtures'], [])        # cleanup happened before the blocked write
        self.assertNotEqual(r['report']['verdict'], 'PASS')

    def test_launcher_hard_stops_an_uninterruptible_supervisor(self):
        r = self.r['launcher_hard_stop']
        self.assertEqual(r['rc'], 123)             # launcher killed its owned child at 30 s
        self.assertGreaterEqual(r['elapsed'], 29.5)
        self.assertLess(r['elapsed'], 32)
        self.assertEqual(r['survivors'], [])
        self.assertEqual(r['fixtures'], [])        # trial and cleanup were already complete
        self.assertEqual(r['gate'], 'REJECT')

    def test_launcher_death_leaves_a_complete_looking_log_that_is_rejected(self):
        r = self.r['launcher_killed']
        self.assertTrue(r['held_seen'])
        self.assertEqual(r['rc'], -signal.SIGKILL)
        self.assertEqual(records(r['out'], 'END'), ['result=complete'])   # the supervisor carried on
        self.assertEqual(r['report']['verdict'], 'PASS')
        self.assertEqual(r['gate'], 'REJECT')      # no acceptance without the controller's exit 0
        self.assertEqual(r['survivors'], [])

    def test_supervisor_death_leaves_children_self_bounded_and_unsignalled(self):
        r = self.r['supervisor_killed']
        self.assertTrue(r['held_seen'])
        self.assertEqual(r['rc'], 137)             # launcher reports its child's SIGKILL
        self.assertEqual(r['out'], b'')            # buffered log is lost: no PASS possible
        self.assertEqual(r['report']['verdict'], 'MALFORMED')
        gone = r['after_kill']
        self.assertEqual(sorted(gone), sorted(['/dev/shmem/' + PROVIDER_PIN, '/dev/shmem/' + READER_PIN]))
        self.assertTrue(all(t is not None for t in gone.values()), gone)
        self.assertLess(gone['/dev/shmem/' + PROVIDER_PIN], 4)  # provider: its own 3 s stand-in lease
        self.assertGreater(gone['/dev/shmem/' + READER_PIN], 12)  # reader: still held until its own
        self.assertLess(gone['/dev/shmem/' + READER_PIN], 20)     # 18 s hold alarm ends it
        self.assertEqual(r['survivors'], [])
        fixture = r['trial'].root / 'ramdisk_mm' / r['fixtures'][0]
        reader_out = (fixture / 'reader.out').read_bytes()
        self.assertTrue(reader_out.endswith(b' offset=100\n'))
        self.assertNotIn(b'RELEASED', reader_out)  # nobody released or probed it
        self.assertEqual(sorted(p.name for p in fixture.iterdir()),
                         ['dummy-body.bin', 'provider.err', 'provider.out', 'reader.err', 'reader.out'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
