#!/usr/bin/env python3
"""Runner control flow with ordinary host files and the real C reader source."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

from test_body import expected_body
ROOT = Path(__file__).resolve().parent
SCRIPT = (ROOT / 'check_large_alias.sh').read_text()


class Runner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='nbt-stdio-runner-')
        cls.root = Path(cls.temp.name)
        source = (ROOT / 'nbt_large_reader.c').read_text()
        assert source.count('/ramdisk/mm') == 1
        private = cls.root / 'reader.c'
        private.write_text(source.replace('/ramdisk/mm', str(cls.root / 'ram')))
        cls.reader = cls.root / 'reader'
        subprocess.run(['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I',str(ROOT),str(private),str(ROOT/'large_body.c'), '-o', str(cls.reader)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.ram = self.root / 'ram'
        self.ram.mkdir()
        self.helper = self.root / 'helper'
        self.payload = self.root / 'fixture-body'
        self.payload.write_bytes(expected_body(586))
        self.helper.write_text('''#!/usr/bin/env python3
import os,signal,time
from pathlib import Path
root=Path(__file__).parent
endpoint=root/('endpoint.'+str(os.getpid()))
scenario=os.environ.get('NBT_RUNNER_FIXTURE','normal')
def stop(number,frame):
    endpoint.unlink(missing_ok=True)
    raise SystemExit(2)
signal.signal(signal.SIGTERM,stop)
if scenario=='missing_endpoint': raise SystemExit(1)
endpoint.write_bytes((root/'fixture-body').read_bytes())
if scenario=='unexpected':
    next((root/'ram').glob('.nbt-large-alias-586.*')).joinpath('.unexpected').write_text('preserve')
time.sleep(30 if scenario=='overrun' else 0.3)
endpoint.unlink(missing_ok=True)
''')
        self.helper.chmod(0o700)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.bin / 'sleep').write_text('#!/usr/bin/env python3\nimport sys,time\ntime.sleep(float(sys.argv[1])*0.05)\n')
        (self.bin / 'sleep').chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'])
        self.script = self.root / 'check.sh'
        self.write_script()

    def tearDown(self):
        # Test-owned temp tree only; includes intentional preserved failure fixtures.
        import shutil
        shutil.rmtree(self.ram)
        shutil.rmtree(self.bin)
        self.helper.unlink()
        self.payload.unlink()
        for path in self.root.glob('endpoint.*'):
            path.unlink()
        for name in ('fake-reader','linked-reader'):
            path = self.root / name
            if path.exists() or path.is_symlink(): path.unlink()

    def write_script(self, reader=None):
        self.script.write_text(SCRIPT.replace('/ramdisk/mm', str(self.ram))
                               .replace('/dev/shmem/nbt_large_endpoint_586_8f502b6394a0',str(self.helper))
                               .replace('/dev/shmem/nbt_large_reader_586_f0d391701c69',str(reader or self.reader))
                               .replace('/dev/nbt_large_endpoint_586.',str(self.root/'endpoint.')))

    def run_case(self, args=('--rehearse',), scenario='normal'):
        return subprocess.run(['sh',str(self.script),*args],
                              env=dict(self.env,NBT_RUNNER_FIXTURE=scenario),
                              capture_output=True,text=True,timeout=5)

    def assert_clean(self):
        self.assertEqual(list(self.ram.iterdir()),[])

    def test_help_and_bad_arguments_do_not_create_fixtures(self):
        for args,code in (((),0),(('--help',),0),(('--bad',),2),(('--rehearse','extra'),2)):
            result=self.run_case(args)
            self.assertEqual(result.returncode,code,result.stdout+result.stderr)
            self.assert_clean()
            self.assertEqual(list(self.root.glob('endpoint.*')),[])

    def test_missing_reader_is_refused_before_fixture_creation(self):
        self.write_script(self.root/'absent-reader')
        result=self.run_case()
        self.assertEqual(result.returncode,1)
        self.assertIn('reviewed RAM reader unavailable',result.stdout)
        self.assert_clean()

    def test_linked_reader_is_refused(self):
        linked=self.root/'linked-reader'
        linked.symlink_to(self.reader)
        self.write_script(linked)
        result=self.run_case()
        self.assertEqual(result.returncode,1)
        self.assert_clean()

    def test_real_host_reader_passes_then_alias_expires_and_cleans(self):
        result=self.run_case()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PASS: larger-reader-1; bytes=586 items=1',result.stdout)
        self.assertIn('Stdio reader exit: 0',result.stdout)
        self.assertIn('Endpoint server exit: 0',result.stdout)
        self.assertIn('DANGLING:',result.stdout)
        self.assertIn('PASS: 586-byte dummy reader/expiry/cleanup; trace requires assessment',result.stdout)
        self.assert_clean()

    def test_failed_reader_cannot_count_as_success(self):
        fake=self.root/'fake-reader'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o700)
        self.write_script(fake)
        result=self.run_case()
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertIn('STOP: stdio reader failed',result.stdout)
        self.assertNotIn('PASS:',result.stdout)
        self.assert_clean()

    def test_missing_endpoint_stops_and_cleans(self):
        result=self.run_case(scenario='missing_endpoint')
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertIn('endpoint not ready',result.stdout)
        self.assertNotIn('PASS:',result.stdout)
        self.assert_clean()

    def test_overrun_is_not_a_runner_pass(self):
        result=self.run_case(scenario='overrun')
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertIn('WATCHDOG:',result.stdout)
        self.assertIn('STOP: unexpected helper exit',result.stdout)
        self.assertNotIn('PASS: 586-byte dummy reader/expiry/cleanup',result.stdout)
        self.assert_clean()

    def test_unexpected_hidden_file_is_preserved(self):
        result=self.run_case(scenario='unexpected')
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertIn('unexpected fixture entry',result.stdout)
        self.assertNotIn('PASS: 586-byte dummy reader/expiry/cleanup',result.stdout)
        fixture=next(self.ram.iterdir())
        self.assertEqual((fixture/'.unexpected').read_text(),'preserve')
        self.assertFalse((fixture/'dummy-body.bin').is_symlink())

    def test_hangup_attempts_owned_fixture_cleanup(self):
        process=subprocess.Popen(['sh',str(self.script),'--rehearse'],env=self.env,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                if any(p.is_symlink() for p in self.ram.glob('*/dummy-body.bin')):break
                time.sleep(0.005)
            else:self.fail('alias did not appear')
            process.send_signal(signal.SIGHUP)
            out,err=process.communicate(timeout=4)
            self.assertEqual(process.returncode,2,out+err)
            self.assertNotIn('PASS: 586-byte dummy reader/expiry/cleanup',out)
            self.assert_clean()
        finally:
            if process.poll() is None:process.kill();process.wait()


if __name__=='__main__':unittest.main(verbosity=2)
